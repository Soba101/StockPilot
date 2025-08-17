"use client"

import * as React from "react"
import { useForm, UseFormReturn, FieldValues, Path } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { ZodSchema } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { RotateCcw, AlertCircle, CheckCircle2, Loader2, ChevronDown, ChevronRight } from "lucide-react"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

export interface FormSection<T extends FieldValues = FieldValues> {
  id: string
  title: string
  description?: string
  fields: (keyof T)[]
  collapsible?: boolean
  defaultExpanded?: boolean
  badge?: string
  validation?: {
    level: "info" | "warning" | "error"
    message: string
  }
}

export interface SettingsFormProps<T extends FieldValues> {
  schema: ZodSchema<T>
  defaultValues: T
  onSubmit: (data: T) => Promise<void>
  sections?: FormSection<T>[]
  children: React.ReactNode
  autoSave?: boolean
  saveInterval?: number
  showResetButton?: boolean
  submitButtonText?: string
  resetButtonText?: string
  className?: string
}

export interface SettingsFormContext<T extends FieldValues> {
  form: UseFormReturn<T>
  isSubmitting: boolean
  isDirty: boolean
  autoSave: boolean
}

const SettingsFormContext = React.createContext<SettingsFormContext<FieldValues> | null>(null)

export function useSettingsForm<T extends FieldValues>() {
  const context = React.useContext(SettingsFormContext)
  if (!context) {
    throw new Error("useSettingsForm must be used within a SettingsForm")
  }
  return context as SettingsFormContext<T>
}

export function SettingsForm<T extends FieldValues>({
  schema,
  defaultValues,
  onSubmit,
  sections = [],
  children,
  autoSave = true,
  saveInterval = 2000,
  showResetButton = true,
  submitButtonText = "Save Changes",
  resetButtonText = "Reset",
  className,
}: SettingsFormProps<T>) {
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [submitStatus, setSubmitStatus] = React.useState<"idle" | "success" | "error">("idle")
  const [autoSaveTimer, setAutoSaveTimer] = React.useState<NodeJS.Timeout | null>(null)
  const [expandedSections, setExpandedSections] = React.useState<Set<string>>(
    new Set(sections.filter(s => s.defaultExpanded !== false).map(s => s.id))
  )

  const form = useForm<T>({
    resolver: zodResolver(schema),
    defaultValues,
    mode: "onChange",
  })

  const { handleSubmit, reset, formState: { isDirty, isValid, errors } } = form

  const handleFormSubmit = React.useCallback(async (data: T) => {
    setIsSubmitting(true)
    setSubmitStatus("idle")
    
    try {
      await onSubmit(data)
      setSubmitStatus("success")
      
      // Clear success status after 3 seconds
      setTimeout(() => setSubmitStatus("idle"), 3000)
    } catch (error) {
      setSubmitStatus("error")
      console.error("Form submission error:", error)
    } finally {
      setIsSubmitting(false)
    }
  }, [onSubmit])

  // Auto-save functionality
  const watchedValues = form.watch()
  React.useEffect(() => {
    if (autoSave && isDirty && isValid) {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
      }
      
      const timer = setTimeout(() => {
        handleSubmit(handleFormSubmit)()
      }, saveInterval)
      
      setAutoSaveTimer(timer)
    }

    return () => {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
      }
    }
  }, [watchedValues, autoSave, isDirty, isValid, saveInterval, autoSaveTimer, handleSubmit, handleFormSubmit])

  const handleReset = () => {
    reset(defaultValues)
    setSubmitStatus("idle")
  }

  const toggleSection = (sectionId: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev)
      if (newSet.has(sectionId)) {
        newSet.delete(sectionId)
      } else {
        newSet.add(sectionId)
      }
      return newSet
    })
  }

  const getSubmitButtonContent = () => {
    if (isSubmitting) {
      return (
        <>
          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          {autoSave ? "Saving..." : "Submitting..."}
        </>
      )
    }
    
    if (submitStatus === "success") {
      return (
        <>
          <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />
          Saved
        </>
      )
    }
    
    return submitButtonText
  }

  const contextValue: SettingsFormContext<T> = {
    form,
    isSubmitting,
    isDirty,
    autoSave,
  }

  return (
    <SettingsFormContext.Provider value={contextValue}>
      <form onSubmit={handleSubmit(handleFormSubmit)} className={cn("space-y-6", className)}>
        {/* Form Status Alert */}
        {submitStatus === "error" && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              There was an error saving your changes. Please try again.
            </AlertDescription>
          </Alert>
        )}

        {/* Sectioned Content */}
        {sections.length > 0 ? (
          <div className="space-y-4">
            {sections.map((section) => {
              const isExpanded = expandedSections.has(section.id)
              const hasErrors = section.fields.some(field => errors[field as Path<T>])
              
              return (
                <Card key={section.id} className={cn(hasErrors && "border-destructive")}>
                  {section.collapsible ? (
                    <Collapsible open={isExpanded} onOpenChange={() => toggleSection(section.id)}>
                      <CollapsibleTrigger asChild>
                        <CardHeader className="cursor-pointer hover:bg-accent/50 transition-colors">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-2">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4" />
                                ) : (
                                  <ChevronRight className="h-4 w-4" />
                                )}
                                <CardTitle className="text-base">{section.title}</CardTitle>
                              </div>
                              {section.badge && (
                                <Badge variant="secondary">{section.badge}</Badge>
                              )}
                              {hasErrors && (
                                <Badge variant="destructive" className="text-xs">
                                  Errors
                                </Badge>
                              )}
                            </div>
                          </div>
                          {section.description && (
                            <CardDescription>{section.description}</CardDescription>
                          )}
                        </CardHeader>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <CardContent>
                          <Separator className="mb-4" />
                          {/* Section validation message */}
                          {section.validation && (
                            <Alert 
                              variant={section.validation.level === "error" ? "destructive" : "default"}
                              className="mb-4"
                            >
                              <AlertCircle className="h-4 w-4" />
                              <AlertDescription>{section.validation.message}</AlertDescription>
                            </Alert>
                          )}
                          <div className="space-y-4">
                            {React.Children.toArray(children).filter((child) => 
                              React.isValidElement(child) && section.fields.includes(child.props?.name)
                            )}
                          </div>
                        </CardContent>
                      </CollapsibleContent>
                    </Collapsible>
                  ) : (
                    <>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <CardTitle className="text-base">{section.title}</CardTitle>
                            {section.badge && (
                              <Badge variant="secondary">{section.badge}</Badge>
                            )}
                            {hasErrors && (
                              <Badge variant="destructive" className="text-xs">
                                Errors
                              </Badge>
                            )}
                          </div>
                        </div>
                        {section.description && (
                          <CardDescription>{section.description}</CardDescription>
                        )}
                      </CardHeader>
                      <CardContent>
                        {/* Section validation message */}
                        {section.validation && (
                          <Alert 
                            variant={section.validation.level === "error" ? "destructive" : "default"}
                            className="mb-4"
                          >
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription>{section.validation.message}</AlertDescription>
                          </Alert>
                        )}
                        <div className="space-y-4">
                          {React.Children.toArray(children).filter((child) => 
                            React.isValidElement(child) && section.fields.includes(child.props?.name)
                          )}
                        </div>
                      </CardContent>
                    </>
                  )}
                </Card>
              )
            })}
          </div>
        ) : (
          /* Non-sectioned content */
          <div className="space-y-4">
            {children}
          </div>
        )}

        {/* Form Actions */}
        {!autoSave && (
          <div className="flex items-center justify-between pt-6 border-t">
            <div className="text-sm text-muted-foreground">
              {isDirty ? "You have unsaved changes" : "No changes to save"}
            </div>
            <div className="flex items-center gap-3">
              {showResetButton && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={isSubmitting || !isDirty}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  {resetButtonText}
                </Button>
              )}
              <Button
                type="submit"
                disabled={isSubmitting || !isDirty || !isValid}
                variant={submitStatus === "success" ? "default" : "default"}
              >
                {getSubmitButtonContent()}
              </Button>
            </div>
          </div>
        )}
      </form>
    </SettingsFormContext.Provider>
  )
}