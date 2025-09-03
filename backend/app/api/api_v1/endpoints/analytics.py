from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from sqlalchemy.exc import ProgrammingError
from datetime import datetime, timedelta, date
from app.core.database import get_db, get_current_claims
from app.models.product import Product
from app.models.order import Order, OrderItem
from pydantic import BaseModel

router = APIRouter()


class SalesMetrics(BaseModel):
    total_revenue: float
    total_units: int
    avg_order_value: float
    total_orders: int
    revenue_growth: float
    units_growth: float


class TopProduct(BaseModel):
    name: str
    sku: str
    units: int
    revenue: float
    margin: float


class CategoryData(BaseModel):
    category: str
    revenue: float
    percentage: float
    growth: float


class RecentSale(BaseModel):
    date: str
    product: str
    quantity: int
    revenue: float
    channel: str


class RevenuePoint(BaseModel):
    date: str
    revenue: float


class AnalyticsResponse(BaseModel):
    sales_metrics: SalesMetrics
    top_products: List[TopProduct]
    category_data: List[CategoryData]
    recent_sales: List[RecentSale]
    revenue_trend: List[RevenuePoint]


class DailySalesData(BaseModel):
    sales_date: str
    channel: str
    location_name: str
    product_name: str
    sku: str
    category: str
    units_sold: int
    gross_revenue: float
    gross_margin: float
    margin_percent: float
    orders_count: int
    units_7day_avg: float
    units_30day_avg: float


class ChannelPerformance(BaseModel):
    channel: str
    total_revenue: float
    total_units: int
    orders_count: int
    avg_order_value: float
    margin_percent: float


class SalesAnalyticsResponse(BaseModel):
    period_summary: dict
    daily_sales: List[DailySalesData]
    channel_performance: List[ChannelPerformance]
    top_performing_products: List[dict]
    trending_analysis: dict


class StockoutRisk(BaseModel):
    product_id: str
    product_name: str
    sku: str
    on_hand: float
    reorder_point: Optional[int]
    velocity_7d: Optional[float]
    velocity_30d: Optional[float]
    days_to_stockout: Optional[float]
    risk_level: str  # none|low|medium|high
    # W4 additive fields (kept optional for backward compatibility)
    velocity_source: Optional[str] = None  # 7d|30d|56d|none
    velocity_56d: Optional[float] = None
    forecast_30d_units: Optional[float] = None


@router.get("", response_model=AnalyticsResponse)
def get_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get comprehensive analytics data for the specified period"""
    
    org_id = claims.get("org")
    
    # Get all orders for this organization
    orders = db.query(Order).filter(Order.org_id == org_id).all()
    
    # Enhanced sales metrics using sales_daily mart for recent period
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get metrics from sales_daily mart if available
    mart_query = """
        SELECT 
            sum(gross_revenue) as total_revenue,
            sum(units_sold) as total_units,
            sum(orders_count) as total_orders,
            avg(margin_percent) as avg_margin
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
    """
    
    try:
        mart_result = db.execute(text(mart_query), {
            "org_id": org_id,
            "start_date": start_date,
            "end_date": end_date
        }).fetchone()
        
        if mart_result and mart_result.total_revenue:
            # Use mart data
            total_revenue = float(mart_result.total_revenue)
            total_units = int(mart_result.total_units)
            total_orders = int(mart_result.total_orders)
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        else:
            raise Exception("No mart data available")
            
    except Exception:
        # Fall back to original method if mart is not available
        fulfilled_orders = [o for o in orders if o.status == 'completed']
        total_revenue = sum(float(order.total_amount or 0) for order in fulfilled_orders)
        total_orders = len(fulfilled_orders)
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Get order items for units calculation
        order_items = db.query(OrderItem).join(Order).filter(
            Order.org_id == org_id,
            Order.status == 'completed'
        ).all()
        
        total_units = sum(item.quantity for item in order_items)
    
    sales_metrics = SalesMetrics(
        total_revenue=total_revenue,
        total_units=total_units,
        avg_order_value=avg_order_value,
        total_orders=total_orders,
        revenue_growth=12.5,  # Mock growth for now
        units_growth=-2.3     # Mock growth for now
    )
    
    # Top products
    product_sales = db.query(
        Product.name,
        Product.sku,
        func.sum(OrderItem.quantity).label('total_units'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_revenue'),
        Product.cost,
        Product.price
    ).select_from(Product).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).filter(
        Order.org_id == org_id,
        Order.status == 'completed'
    ).group_by(Product.id, Product.name, Product.sku, Product.cost, Product.price).order_by(
        desc('total_revenue')
    ).limit(5).all()
    
    top_products = []
    for row in product_sales:
        if row.total_revenue:  # Only include products with sales
            cost = float(row.cost or 0)
            price = float(row.price or 0)
            margin = ((price - cost) / price * 100) if price > 0 else 0
            
            top_products.append(TopProduct(
                name=row.name,
                sku=row.sku,
                units=int(row.total_units),
                revenue=float(row.total_revenue),
                margin=round(margin, 1)
            ))
    
    # Category data
    category_sales = db.query(
        Product.category,
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue')
    ).select_from(Product).join(OrderItem, Product.id == OrderItem.product_id).join(Order, OrderItem.order_id == Order.id).filter(
        Order.org_id == org_id,
        Order.status == 'completed',
        Product.category.isnot(None)
    ).group_by(Product.category).all()
    
    total_category_revenue = sum(float(row.revenue) for row in category_sales if row.revenue)
    
    category_data = []
    for row in category_sales:
        if row.revenue:  # Only include categories with sales
            revenue = float(row.revenue)
            percentage = (revenue / total_category_revenue * 100) if total_category_revenue > 0 else 0
            
            category_data.append(CategoryData(
                category=row.category,
                revenue=revenue,
                percentage=round(percentage, 1),
                growth=round((hash(row.category) % 20) - 10, 1)  # Mock growth data
            ))
    
    # Recent sales
    recent_sales_data = db.query(
        Order.ordered_at,
        Product.name,
        OrderItem.quantity,
        OrderItem.unit_price,
        Order.channel
    ).select_from(Order).join(OrderItem, Order.id == OrderItem.order_id).join(Product, OrderItem.product_id == Product.id).filter(
        Order.org_id == org_id,
        Order.status == 'completed'
    ).order_by(desc(Order.ordered_at)).limit(10).all()
    
    recent_sales = []
    for row in recent_sales_data:
        recent_sales.append(RecentSale(
            date=row.ordered_at.strftime('%Y-%m-%d') if row.ordered_at else '2025-01-01',
            product=row.name,
            quantity=row.quantity,
            revenue=float(row.quantity * row.unit_price),
            channel=row.channel or 'Unknown'
        ))
    
    # Enhanced revenue trend using sales_daily mart
    revenue_trend = []
    
    try:
        trend_query = """
            SELECT 
                sales_date,
                sum(gross_revenue) as daily_revenue
            FROM analytics_marts.sales_daily
            WHERE org_id = :org_id
              AND sales_date >= :trend_start_date
            GROUP BY sales_date
            ORDER BY sales_date
        """
        
        trend_start_date = end_date - timedelta(days=7)  # Last 7 days
        trend_result = db.execute(text(trend_query), {
            "org_id": org_id,
            "trend_start_date": trend_start_date
        }).fetchall()
        
        if trend_result:
            for row in trend_result:
                revenue_trend.append(RevenuePoint(
                    date=row.sales_date.strftime('%m-%d'),
                    revenue=float(row.daily_revenue)
                ))
        else:
            raise Exception("No mart trend data available")
            
    except Exception:
        # Fall back to original method
        completed_orders = [o for o in orders if o.status == 'completed']
        if completed_orders:
            # Group orders by date
            from collections import defaultdict
            daily_revenue = defaultdict(float)
            
            for order in completed_orders:
                if order.ordered_at:
                    date_str = order.ordered_at.strftime('%m-%d')
                    daily_revenue[date_str] += float(order.total_amount or 0)
            
            # Convert to list and fill in missing days with 0
            for date_str, revenue in daily_revenue.items():
                revenue_trend.append(RevenuePoint(
                    date=date_str,
                    revenue=revenue
                ))
            
            # Sort by date
            revenue_trend.sort(key=lambda x: x.date)
    
    # If no revenue trend data, create some basic data points
    if not revenue_trend:
        base_revenue = 1000
        for i in range(7):
            day = datetime.now() - timedelta(days=6-i)
            revenue_trend.append(RevenuePoint(
                date=day.strftime('%m-%d'),
                revenue=base_revenue + (i * 200)
            ))
    
    return AnalyticsResponse(
        sales_metrics=sales_metrics,
        top_products=top_products,
        category_data=category_data,
        recent_sales=recent_sales,
        revenue_trend=revenue_trend
    )


@router.get("/sales", response_model=SalesAnalyticsResponse)
def get_sales_analytics(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze (if dates not provided)"),
    channel: Optional[str] = Query(None, description="Filter by sales channel"),
    product_category: Optional[str] = Query(None, description="Filter by product category"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Get detailed sales analytics from the sales_daily dbt mart"""
    
    org_id = claims.get("org")
    
    # Set date range
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        start_date = end_date - timedelta(days=days)
    
    # Query the sales_daily mart
    base_query = """
        SELECT 
            sales_date,
            channel,
            location_name,
            product_name,
            sku,
            category,
            units_sold,
            gross_revenue,
            gross_margin,
            margin_percent,
            orders_count,
            coalesce(units_7day_avg, 0) as units_7day_avg,
            coalesce(units_30day_avg, 0) as units_30day_avg
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
    """
    
    params = {
        "org_id": org_id,
        "start_date": start_date,
        "end_date": end_date
    }
    
    # Add filters
    if channel:
        base_query += " AND channel = :channel"
        params["channel"] = channel
    
    if product_category:
        base_query += " AND category = :product_category"
        params["product_category"] = product_category
    
    base_query += " ORDER BY sales_date DESC, gross_revenue DESC"
    
    # Execute query with fallback pattern
    daily_sales_raw = []
    try:
        # Try mart query first
        result = db.execute(text(base_query), params)
        daily_sales_raw = result.fetchall()
        if not daily_sales_raw:
            raise Exception("No mart data available")
    except Exception:
        # Fallback to raw tables
        db.rollback()
        fallback_query = """
            SELECT 
                o.ordered_at::date as sales_date,
                COALESCE(o.channel, 'Unknown') as channel,
                COALESCE(l.name, 'Unknown') as location_name,
                p.name as product_name,
                p.sku,
                COALESCE(p.category, 'Uncategorized') as category,
                oi.quantity as units_sold,
                (oi.unit_price * oi.quantity - oi.discount) as gross_revenue,
                ((oi.unit_price - p.cost) * oi.quantity) as gross_margin,
                CASE 
                    WHEN oi.unit_price > 0 THEN ((oi.unit_price - p.cost) / oi.unit_price * 100)
                    ELSE 0 
                END as margin_percent,
                1 as orders_count,
                0 as units_7day_avg,
                0 as units_30day_avg
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            LEFT JOIN locations l ON o.location_id = l.id
            WHERE o.org_id = :org_id
              AND o.ordered_at::date BETWEEN :start_date AND :end_date
              AND o.status IN ('fulfilled', 'completed', 'shipped')
        """
        
        # Add the same filters for fallback
        if channel:
            fallback_query += " AND COALESCE(o.channel, 'Unknown') = :channel"
        if product_category:
            fallback_query += " AND COALESCE(p.category, 'Uncategorized') = :product_category"
            
        fallback_query += " ORDER BY o.ordered_at DESC, gross_revenue DESC"
        
        result = db.execute(text(fallback_query), params)
        daily_sales_raw = result.fetchall()
    
    # Convert to Pydantic models
    daily_sales = []
    for row in daily_sales_raw:
        daily_sales.append(DailySalesData(
            sales_date=row.sales_date.strftime('%Y-%m-%d'),
            channel=row.channel or 'Unknown',
            location_name=row.location_name or 'Unknown',
            product_name=row.product_name,
            sku=row.sku,
            category=row.category or 'Uncategorized',
            units_sold=int(row.units_sold),
            gross_revenue=float(row.gross_revenue),
            gross_margin=float(row.gross_margin),
            margin_percent=float(row.margin_percent),
            orders_count=int(row.orders_count),
            units_7day_avg=float(row.units_7day_avg),
            units_30day_avg=float(row.units_30day_avg)
        ))
    
    # Calculate period summary
    total_revenue = sum(row.gross_revenue for row in daily_sales_raw)
    total_units = sum(row.units_sold for row in daily_sales_raw)
    total_margin = sum(row.gross_margin for row in daily_sales_raw)
    total_orders = sum(row.orders_count for row in daily_sales_raw)
    
    period_summary = {
        "total_revenue": float(total_revenue),
        "total_units": int(total_units),
        "total_margin": float(total_margin),
        "total_orders": int(total_orders),
        "avg_order_value": float(total_revenue / total_orders) if total_orders > 0 else 0,
        "avg_margin_percent": float(total_margin / total_revenue * 100) if total_revenue > 0 else 0,
        "date_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": (end_date - start_date).days + 1
        }
    }
    
    # Channel performance analysis
    channel_query = """
        SELECT 
            channel,
            sum(gross_revenue) as total_revenue,
            sum(units_sold) as total_units,
            sum(orders_count) as orders_count,
            avg(margin_percent) as avg_margin_percent
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
        GROUP BY channel
        ORDER BY total_revenue DESC
    """
    
    channel_result = db.execute(text(channel_query), params)
    channel_data = []
    for row in channel_result.fetchall():
        channel_data.append(ChannelPerformance(
            channel=row.channel or 'Unknown',
            total_revenue=float(row.total_revenue),
            total_units=int(row.total_units),
            orders_count=int(row.orders_count),
            avg_order_value=float(row.total_revenue / row.orders_count) if row.orders_count > 0 else 0,
            margin_percent=float(row.avg_margin_percent)
        ))
    
    # Top performing products
    top_products_query = """
        SELECT 
            product_name,
            sku,
            category,
            sum(gross_revenue) as total_revenue,
            sum(units_sold) as total_units,
            avg(margin_percent) as avg_margin_percent,
            avg(units_7day_avg) as avg_velocity
        FROM analytics_marts.sales_daily
        WHERE org_id = :org_id
          AND sales_date BETWEEN :start_date AND :end_date
        GROUP BY product_name, sku, category
        ORDER BY total_revenue DESC
        LIMIT 10
    """
    
    top_products_result = db.execute(text(top_products_query), params)
    top_performing_products = []
    for row in top_products_result.fetchall():
        top_performing_products.append({
            "product_name": row.product_name,
            "sku": row.sku,
            "category": row.category or 'Uncategorized',
            "total_revenue": float(row.total_revenue),
            "total_units": int(row.total_units),
            "avg_margin_percent": float(row.avg_margin_percent),
            "avg_velocity": float(row.avg_velocity)
        })
    
    # Trending analysis
    trending_analysis = {
        "growth_products": [],
        "declining_products": [],
        "volatile_products": []
    }
    
    # Simple trending analysis based on 7-day vs 30-day averages
    if daily_sales_raw:
        for row in daily_sales_raw:
            if row.units_30day_avg > 0:
                trend_ratio = row.units_7day_avg / row.units_30day_avg
                
                if trend_ratio > 1.2:  # 20% above average
                    trending_analysis["growth_products"].append({
                        "product_name": row.product_name,
                        "sku": row.sku,
                        "trend_ratio": round(trend_ratio, 2)
                    })
                elif trend_ratio < 0.8:  # 20% below average
                    trending_analysis["declining_products"].append({
                        "product_name": row.product_name,
                        "sku": row.sku,
                        "trend_ratio": round(trend_ratio, 2)
                    })
        
        # Limit to top 5 each
        trending_analysis["growth_products"] = trending_analysis["growth_products"][:5]
        trending_analysis["declining_products"] = trending_analysis["declining_products"][:5]
    
    return SalesAnalyticsResponse(
        period_summary=period_summary,
        daily_sales=daily_sales,
        channel_performance=channel_data,
        top_performing_products=top_performing_products,
        trending_analysis=trending_analysis
    )


@router.get("/stockout-risk", response_model=List[StockoutRisk])
def get_stockout_risk(
    days: int = Query(30, ge=7, le=120, description="Lookback window for velocity context"),
    velocity_strategy: str = Query("latest", pattern="^(latest|conservative)$", description="Velocity selection strategy"),
    db: Session = Depends(get_db),
    claims = Depends(get_current_claims),
):
    """Return per-product stockout risk metrics combining current stock & sales velocity.

    days_to_stockout = on_hand / max(velocity_7d, velocity_30d, epsilon)
    Velocity source: sales_daily mart rolling averages (already precomputed).
    Risk bands (only if velocity > 0):
      <=7 days => high, <=14 => medium, <=30 => low, else none.
    """

    org_id = claims.get("org")

    # Current on hand per product
    stock_sql = text("""
        SELECT p.id as product_id, p.name as product_name, p.sku, p.reorder_point,
               COALESCE(SUM(CASE 
                 WHEN im.movement_type IN ('in','adjust') THEN im.quantity
                 WHEN im.movement_type = 'out' THEN -im.quantity
                 WHEN im.movement_type = 'transfer' THEN 0
                 ELSE 0 END), 0) as on_hand
        FROM products p
        LEFT JOIN inventory_movements im ON im.product_id = p.id
        WHERE p.org_id = :org_id
        GROUP BY p.id, p.name, p.sku, p.reorder_point
    """)

    stock_rows = db.execute(stock_sql, {"org_id": org_id}).fetchall()
    stock_map = {str(r.product_id): r for r in stock_rows}

    # Velocity (average of rolling averages over window)
    velocity_sql = text("""
        SELECT sd.sku, 
                             AVG(sd.units_7day_avg) as v7,
                             AVG(sd.units_30day_avg) as v30,
                             AVG(sd.units_56day_avg) as v56,
                             AVG(COALESCE(sd.units_7day_avg, sd.units_30day_avg, sd.units_56day_avg) * 30) as forecast_30d
                FROM analytics_marts.sales_daily sd
                WHERE sd.org_id = :org_id
                    AND sd.sales_date >= :start_date
        GROUP BY sd.sku
    """)
    start_date = (datetime.now().date() - timedelta(days=days))
    # Determine if 56-day column exists to avoid broken transaction on missing column
    col_check = db.execute(text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema='analytics_marts' AND table_name='sales_daily' AND column_name='units_56day_avg'
    """)).fetchone()
    if col_check:
        try:
            vel_rows = db.execute(velocity_sql, {"org_id": org_id, "start_date": start_date}).fetchall()
        except ProgrammingError:
            db.rollback()
            vel_rows = []
    else:
        fallback_velocity_sql = text("""
            SELECT sd.sku,
                   AVG(sd.units_7day_avg) as v7,
                   AVG(sd.units_30day_avg) as v30,
                   NULL::numeric as v56,
                   AVG(COALESCE(sd.units_7day_avg, sd.units_30day_avg) * 30) as forecast_30d
            FROM analytics_marts.sales_daily sd
            WHERE sd.org_id = :org_id
              AND sd.sales_date >= :start_date
            GROUP BY sd.sku
        """)
        vel_rows = db.execute(fallback_velocity_sql, {"org_id": org_id, "start_date": start_date}).fetchall()
    velocity_map = {r.sku: r for r in vel_rows}

    results: List[StockoutRisk] = []
    epsilon = 1e-6
    for pid, row in stock_map.items():
        vel_row = velocity_map.get(row.sku)
        v7 = float(vel_row.v7) if vel_row and vel_row.v7 is not None else None
        v30 = float(vel_row.v30) if vel_row and vel_row.v30 is not None else None
        v56 = float(vel_row.v56) if vel_row and vel_row.v56 is not None else None
        forecast_30d = float(vel_row.forecast_30d) if vel_row and vel_row.forecast_30d is not None else None

        chosen_velocity = None
        velocity_source = "none"
        candidates = [v for v in [v7, v30, v56] if v and v > 0]
        if velocity_strategy == "latest":
            for val, src in [(v7, "7d"), (v30, "30d"), (v56, "56d")]:
                if val and val > 0:
                    chosen_velocity = val
                    velocity_source = src
                    break
        else:  # conservative
            if candidates:
                chosen_velocity = min(candidates)
                if chosen_velocity == v7:
                    velocity_source = "7d"
                elif chosen_velocity == v30:
                    velocity_source = "30d"
                elif chosen_velocity == v56:
                    velocity_source = "56d"

        days_to_stockout = None
        if chosen_velocity and chosen_velocity > 0:
            days_to_stockout = float(row.on_hand) / max(chosen_velocity, epsilon)

        # Determine risk level
        risk_level = "none"
        if days_to_stockout is not None:
            if days_to_stockout <= 7:
                risk_level = "high"
            elif days_to_stockout <= 14:
                risk_level = "medium"
            elif days_to_stockout <= 30:
                risk_level = "low"

        # Elevate risk if below reorder point regardless of velocity
        if row.reorder_point is not None and float(row.on_hand) <= float(row.reorder_point or 0):
            # Only upgrade risk if not already high
            if risk_level in ("none", "low"):
                risk_level = "medium" if risk_level == "none" else risk_level

        results.append(StockoutRisk(
            product_id=pid,
            product_name=row.product_name,
            sku=row.sku,
            on_hand=float(row.on_hand),
            reorder_point=int(row.reorder_point) if row.reorder_point is not None else None,
            velocity_7d=v7,
            velocity_30d=v30,
            days_to_stockout=round(days_to_stockout, 1) if days_to_stockout is not None else None,
            risk_level=risk_level,
            velocity_source=velocity_source,
            velocity_56d=v56,
            forecast_30d_units=forecast_30d
        ))

    # Sort by highest risk then shortest days_to_stockout
    def sort_key(r: StockoutRisk):
        risk_rank = {"high": 0, "medium": 1, "low": 2, "none": 3}.get(r.risk_level, 4)
        return (risk_rank, r.days_to_stockout if r.days_to_stockout is not None else 9999)

    results.sort(key=sort_key)
    return results