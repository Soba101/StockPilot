from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta, date
from app.core.database import get_db, get_current_claims
from pydantic import BaseModel
import json
import io
import csv

router = APIRouter()


class WeeklyMetrics(BaseModel):
    period_start: str
    period_end: str
    total_revenue: float
    total_units: int
    total_orders: int
    avg_order_value: float
    gross_margin: float
    margin_percent: float
    revenue_change_percent: float
    units_change_percent: float


class TopPerformer(BaseModel):
    name: str
    sku: str
    category: str
    revenue: float
    units: int
    margin_percent: float
    rank: int


class InventoryAlert(BaseModel):
    product_name: str
    sku: str
    location_name: str
    current_stock: int
    reorder_point: int
    alert_type: str  # 'low_stock', 'out_of_stock', 'overstock'
    days_until_stockout: Optional[int]


class ChannelInsight(BaseModel):
    channel: str
    revenue: float
    units: int
    orders: int
    growth_percent: float
    market_share_percent: float


class WeekInReviewReport(BaseModel):
    report_id: str
    generated_at: str
    period: WeeklyMetrics
    top_products: List[TopPerformer]
    inventory_alerts: List[InventoryAlert]
    channel_insights: List[ChannelInsight]
    key_insights: List[str]
    recommendations: List[str]
    summary: Dict[str, Any]


@router.get("/week-in-review", response_model=WeekInReviewReport)
def generate_week_in_review(
    start_date: Optional[date] = Query(None, description="Week start date (defaults to last Monday)"),
    end_date: Optional[date] = Query(None, description="Week end date (defaults to last Sunday)"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Generate a comprehensive Week in Review report using sales_daily mart and inventory data"""
    
    org_id = claims.get("org")
    report_id = f"WIR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Set default date range to last week (Monday to Sunday)
    if not start_date or not end_date:
        today = date.today()
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        start_date = start_date or last_monday
        end_date = end_date or last_sunday
    
    # Previous week for comparison
    prev_start_date = start_date - timedelta(days=7)
    prev_end_date = end_date - timedelta(days=7)
    
    # Get current week metrics from sales_daily mart
    current_week_query = """
        SELECT 
            sum(gross_revenue) as total_revenue,
            sum(units_sold) as total_units,
            sum(orders_count) as total_orders,
            sum(gross_margin) as gross_margin
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
    """
    
    current_result = db.execute(text(current_week_query), {
        "org_id": org_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchone()
    
    # Get previous week metrics for comparison
    prev_result = db.execute(text(current_week_query), {
        "org_id": org_id,
        "start_date": prev_start_date,
        "end_date": prev_end_date
    }).fetchone()
    
    # Calculate metrics
    current_revenue = float(current_result.total_revenue or 0)
    current_units = int(current_result.total_units or 0)
    current_orders = int(current_result.total_orders or 0)
    current_margin = float(current_result.gross_margin or 0)
    
    prev_revenue = float(prev_result.total_revenue or 0) if prev_result else 0
    prev_units = int(prev_result.total_units or 0) if prev_result else 0
    
    # Calculate growth percentages
    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    units_change = ((current_units - prev_units) / prev_units * 100) if prev_units > 0 else 0
    
    # Build period metrics
    period = WeeklyMetrics(
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        total_revenue=current_revenue,
        total_units=current_units,
        total_orders=current_orders,
        avg_order_value=current_revenue / current_orders if current_orders > 0 else 0,
        gross_margin=current_margin,
        margin_percent=(current_margin / current_revenue * 100) if current_revenue > 0 else 0,
        revenue_change_percent=round(revenue_change, 1),
        units_change_percent=round(units_change, 1)
    )
    
    # Get top performing products
    top_products_query = """
        SELECT 
            product_name,
            sku,
            category,
            sum(gross_revenue) as total_revenue,
            sum(units_sold) as total_units,
            avg(margin_percent) as avg_margin_percent,
            ROW_NUMBER() OVER (ORDER BY sum(gross_revenue) DESC) as rank
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
        GROUP BY product_name, sku, category
        ORDER BY total_revenue DESC
        LIMIT 10
    """
    
    top_products_result = db.execute(text(top_products_query), {
        "org_id": org_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()
    
    top_products = []
    for row in top_products_result:
        top_products.append(TopPerformer(
            name=row.product_name,
            sku=row.sku,
            category=row.category or 'Uncategorized',
            revenue=float(row.total_revenue),
            units=int(row.total_units),
            margin_percent=float(row.avg_margin_percent),
            rank=int(row.rank)
        ))
    
    # Get inventory alerts using inventory summary
    inventory_alerts_query = """
        SELECT 
            p.name as product_name,
            p.sku,
            l.name as location_name,
            COALESCE(
                (SELECT sum(
                    CASE 
                        WHEN movement_type IN ('in', 'adjust') THEN quantity
                        ELSE -quantity
                    END
                ) FROM inventory_movements im 
                WHERE im.product_id = p.id AND im.location_id = l.id), 0
            ) as current_stock,
            p.reorder_point
        FROM products p
        CROSS JOIN locations l
        WHERE p.org_id = :org_id AND l.org_id = :org_id
        AND (
            COALESCE(
                (SELECT sum(
                    CASE 
                        WHEN movement_type IN ('in', 'adjust') THEN quantity
                        ELSE -quantity
                    END
                ) FROM inventory_movements im 
                WHERE im.product_id = p.id AND im.location_id = l.id), 0
            ) <= p.reorder_point 
            OR 
            COALESCE(
                (SELECT sum(
                    CASE 
                        WHEN movement_type IN ('in', 'adjust') THEN quantity
                        ELSE -quantity
                    END
                ) FROM inventory_movements im 
                WHERE im.product_id = p.id AND im.location_id = l.id), 0
            ) = 0
        )
        ORDER BY current_stock ASC
        LIMIT 20
    """
    
    inventory_result = db.execute(text(inventory_alerts_query), {
        "org_id": org_id
    }).fetchall()
    
    inventory_alerts = []
    for row in inventory_result:
        alert_type = 'out_of_stock' if row.current_stock == 0 else 'low_stock'
        
        inventory_alerts.append(InventoryAlert(
            product_name=row.product_name,
            sku=row.sku,
            location_name=row.location_name,
            current_stock=int(row.current_stock),
            reorder_point=int(row.reorder_point or 0),
            alert_type=alert_type,
            days_until_stockout=None  # Would need sales velocity calculation
        ))
    
    # Get channel insights
    channel_query = """
        SELECT 
            channel,
            sum(gross_revenue) as revenue,
            sum(units_sold) as units,
            sum(orders_count) as orders
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
        GROUP BY channel
        ORDER BY revenue DESC
    """
    
    channel_result = db.execute(text(channel_query), {
        "org_id": org_id,
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()
    
    # Calculate total revenue for market share
    total_channel_revenue = sum(float(row.revenue) for row in channel_result)
    
    channel_insights = []
    for row in channel_result:
        channel_revenue = float(row.revenue)
        market_share = (channel_revenue / total_channel_revenue * 100) if total_channel_revenue > 0 else 0
        
        channel_insights.append(ChannelInsight(
            channel=row.channel or 'Unknown',
            revenue=channel_revenue,
            units=int(row.units),
            orders=int(row.orders),
            growth_percent=0,  # Would need previous period comparison
            market_share_percent=round(market_share, 1)
        ))
    
    # Generate key insights
    key_insights = []
    recommendations = []
    
    # Revenue insights
    if revenue_change > 10:
        key_insights.append(f"Strong revenue growth of {revenue_change:.1f}% compared to previous week")
    elif revenue_change < -10:
        key_insights.append(f"Revenue declined {abs(revenue_change):.1f}% compared to previous week")
        recommendations.append("Review pricing strategy and marketing campaigns")
    
    # Inventory insights
    if len(inventory_alerts) > 0:
        out_of_stock = len([a for a in inventory_alerts if a.alert_type == 'out_of_stock'])
        low_stock = len([a for a in inventory_alerts if a.alert_type == 'low_stock'])
        
        if out_of_stock > 0:
            key_insights.append(f"{out_of_stock} products are completely out of stock")
            recommendations.append("Urgent: Restock out-of-stock items to avoid lost sales")
        
        if low_stock > 0:
            key_insights.append(f"{low_stock} products are below reorder point")
            recommendations.append("Review and place purchase orders for low-stock items")
    
    # Top product insights
    if top_products:
        top_product = top_products[0]
        key_insights.append(f"Top performer: {top_product.name} generated ${top_product.revenue:,.2f}")
        
        if top_product.margin_percent < 20:
            recommendations.append(f"Consider reviewing pricing for {top_product.name} - low margin of {top_product.margin_percent:.1f}%")
    
    # Channel insights
    if len(channel_insights) > 1:
        dominant_channel = channel_insights[0]
        if dominant_channel.market_share_percent > 70:
            key_insights.append(f"{dominant_channel.channel} dominates with {dominant_channel.market_share_percent:.1f}% of sales")
            recommendations.append("Consider diversifying sales channels to reduce dependency")
    
    # Summary statistics
    summary = {
        "performance_score": min(100, max(0, 50 + revenue_change)),  # Base 50, adjust by growth
        "health_indicators": {
            "revenue_trend": "positive" if revenue_change > 0 else "negative" if revenue_change < 0 else "stable",
            "inventory_health": "good" if len(inventory_alerts) < 5 else "needs_attention",
            "channel_diversity": "good" if len(channel_insights) > 1 else "limited"
        },
        "week_highlights": {
            "best_day_revenue": current_revenue / 7,  # Simplified
            "total_customers": current_orders,  # Assuming 1 customer per order
            "avg_items_per_order": current_units / current_orders if current_orders > 0 else 0
        }
    }
    
    return WeekInReviewReport(
        report_id=report_id,
        generated_at=datetime.now().isoformat(),
        period=period,
        top_products=top_products,
        inventory_alerts=inventory_alerts,
        channel_insights=channel_insights,
        key_insights=key_insights,
        recommendations=recommendations,
        summary=summary
    )


@router.get("/week-in-review/historical")
def get_historical_reports(
    limit: int = Query(10, ge=1, le=50, description="Number of reports to return"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get list of previously generated reports (placeholder - would need storage)"""
    
    # This would typically query a reports table in the database
    # For now, return mock historical data
    historical_reports = []
    
    for i in range(min(limit, 4)):  # Mock 4 weeks of historical data
        week_start = date.today() - timedelta(weeks=i+1, days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        
        historical_reports.append({
            "report_id": f"WIR-{week_start.strftime('%Y%m%d')}",
            "period_start": week_start.isoformat(),
            "period_end": week_end.isoformat(),
            "generated_at": (datetime.now() - timedelta(weeks=i)).isoformat(),
            "summary": {
                "total_revenue": 5000 + (i * 500),
                "revenue_change_percent": 5.5 - i,
                "alert_count": 3 + i
            }
        })
    
    return {
        "reports": historical_reports,
        "total_count": len(historical_reports)
    }


@router.get("/week-in-review/export/csv")
def export_week_in_review_csv(
    start_date: Optional[date] = Query(None, description="Week start date"),
    end_date: Optional[date] = Query(None, description="Week end date"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Export Week in Review report as CSV"""
    
    # Generate the report data
    report = generate_week_in_review(start_date, end_date, db, claims)
    
    # Create CSV content
    output = io.StringIO()
    
    # Write summary section
    output.write("WEEK IN REVIEW REPORT\n")
    output.write(f"Report ID: {report.report_id}\n")
    output.write(f"Generated: {report.generated_at}\n")
    output.write(f"Period: {report.period.period_start} to {report.period.period_end}\n\n")
    
    # Write key metrics
    output.write("KEY METRICS\n")
    output.write("Metric,Value,Change %\n")
    output.write(f"Total Revenue,${report.period.total_revenue:,.2f},{report.period.revenue_change_percent:+.1f}%\n")
    output.write(f"Total Units,{report.period.total_units:,},{report.period.units_change_percent:+.1f}%\n")
    output.write(f"Total Orders,{report.period.total_orders:,},\n")
    output.write(f"Avg Order Value,${report.period.avg_order_value:.2f},\n")
    output.write(f"Gross Margin,${report.period.gross_margin:,.2f},\n")
    output.write(f"Margin %,{report.period.margin_percent:.1f}%,\n\n")
    
    # Write top products
    output.write("TOP PRODUCTS\n")
    output.write("Rank,Product Name,SKU,Category,Revenue,Units,Margin %\n")
    for product in report.top_products:
        output.write(f"{product.rank},{product.name},{product.sku},{product.category},${product.revenue:,.2f},{product.units},{product.margin_percent:.1f}%\n")
    output.write("\n")
    
    # Write inventory alerts
    output.write("INVENTORY ALERTS\n")
    output.write("Product,SKU,Location,Current Stock,Reorder Point,Alert Type\n")
    for alert in report.inventory_alerts:
        output.write(f"{alert.product_name},{alert.sku},{alert.location_name},{alert.current_stock},{alert.reorder_point},{alert.alert_type}\n")
    output.write("\n")
    
    # Write channel insights
    output.write("CHANNEL PERFORMANCE\n")
    output.write("Channel,Revenue,Units,Orders,Market Share %\n")
    for channel in report.channel_insights:
        output.write(f"{channel.channel},${channel.revenue:,.2f},{channel.units},{channel.orders},{channel.market_share_percent:.1f}%\n")
    output.write("\n")
    
    # Write key insights
    output.write("KEY INSIGHTS\n")
    for i, insight in enumerate(report.key_insights, 1):
        output.write(f"{i}. {insight}\n")
    output.write("\n")
    
    # Write recommendations
    output.write("RECOMMENDATIONS\n")
    for i, recommendation in enumerate(report.recommendations, 1):
        output.write(f"{i}. {recommendation}\n")
    
    # Prepare response
    output.seek(0)
    filename = f"week-in-review-{report.period.period_start}-to-{report.period.period_end}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/week-in-review/export/json")
def export_week_in_review_json(
    start_date: Optional[date] = Query(None, description="Week start date"),
    end_date: Optional[date] = Query(None, description="Week end date"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Export Week in Review report as JSON"""
    
    # Generate the report data
    report = generate_week_in_review(start_date, end_date, db, claims)
    
    # Convert to JSON
    json_content = report.json(indent=2)
    filename = f"week-in-review-{report.period.period_start}-to-{report.period.period_end}.json"
    
    return StreamingResponse(
        io.BytesIO(json_content.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )