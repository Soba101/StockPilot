"use client"

import * as React from "react"
import { z } from "zod"
import { Controller } from "react-hook-form"
import { SettingsForm, FormSection, useSettingsForm } from "./SettingsForm"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { FileUpload } from "@/components/ui/file-upload"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Building2, MapPin, Phone, Mail, Globe } from "lucide-react"

// Validation schema
const organizationSchema = z.object({
  name: z.string().min(1, "Organization name is required").max(255),
  displayName: z.string().max(255).optional(),
  description: z.string().max(1000).optional(),
  logo: z.string().url().optional().or(z.literal("")),
  website: z.string().url().optional().or(z.literal("")),
  email: z.string().email().optional().or(z.literal("")),
  phone: z.string().max(50).optional(),
  address: z.object({
    street: z.string().max(255).optional(),
    city: z.string().max(100).optional(),
    state: z.string().max(100).optional(),
    postalCode: z.string().max(20).optional(),
    country: z.string().max(100).optional(),
  }).optional(),
  businessDetails: z.object({
    industry: z.string().max(100).optional(),
    size: z.enum(["1-10", "11-50", "51-200", "201-1000", "1000+"]).optional(),
    taxId: z.string().max(50).optional(),
    founded: z.string().max(4).optional(),
  }).optional(),
})

type OrganizationFormData = z.infer<typeof organizationSchema>

const defaultValues: OrganizationFormData = {
  name: "",
  displayName: "",
  description: "",
  logo: "",
  website: "",
  email: "",
  phone: "",
  address: {
    street: "",
    city: "",
    state: "",
    postalCode: "",
    country: "",
  },
  businessDetails: {
    industry: "",
    size: undefined,
    taxId: "",
    founded: "",
  },
}

interface OrganizationSettingsProps {
  initialData?: Partial<OrganizationFormData>
  onSave: (data: OrganizationFormData) => Promise<void>
}

export function OrganizationSettings({ 
  initialData = {}, 
  onSave 
}: OrganizationSettingsProps) {
  const mergedDefaults = { ...defaultValues, ...initialData }

  const sections: FormSection<OrganizationFormData>[] = [
    {
      id: "basic",
      title: "Basic Information",
      description: "Core details about your organization",
      fields: ["name", "displayName", "description", "logo"],
      defaultExpanded: true,
    },
    {
      id: "contact",
      title: "Contact Information",
      description: "How to reach your organization",
      fields: ["website", "email", "phone"],
      defaultExpanded: true,
    },
    {
      id: "address",
      title: "Address",
      description: "Physical location details",
      fields: ["address"],
      collapsible: true,
      defaultExpanded: false,
    },
    {
      id: "business",
      title: "Business Details",
      description: "Additional business information",
      fields: ["businessDetails"],
      collapsible: true,
      defaultExpanded: false,
      badge: "Optional",
    },
  ]

  return (
    <SettingsForm
      schema={organizationSchema}
      defaultValues={mergedDefaults}
      onSubmit={onSave}
      sections={sections}
      autoSave={true}
    >
      <OrganizationFormFields />
    </SettingsForm>
  )
}

function OrganizationFormFields() {
  const { form } = useSettingsForm<OrganizationFormData>()
  const { control, watch, setValue } = form

  const logoUrl = watch("logo")

  const handleLogoUpload = async (files: File[]) => {
    if (files.length > 0) {
      // In a real app, you'd upload to a service and get back a URL
      // For now, we'll create a local URL
      const file = files[0]
      const url = URL.createObjectURL(file)
      setValue("logo", url, { shouldDirty: true })
    }
  }

  return (
    <>
      {/* Basic Information Fields */}
      <div name="name" className="space-y-2">
        <Label htmlFor="org-name">Organization Name *</Label>
        <Controller
          name="name"
          control={control}
          render={({ field, fieldState }) => (
            <Input
              id="org-name"
              placeholder="Enter organization name"
              leftIcon={Building2}
              error={fieldState.error?.message}
              {...field}
            />
          )}
        />
      </div>

      <div name="displayName" className="space-y-2">
        <Label htmlFor="display-name">Display Name</Label>
        <Controller
          name="displayName"
          control={control}
          render={({ field, fieldState }) => (
            <Input
              id="display-name"
              placeholder="Public display name (optional)"
              error={fieldState.error?.message}
              {...field}
            />
          )}
        />
      </div>

      <div name="description" className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Controller
          name="description"
          control={control}
          render={({ field, fieldState }) => (
            <Textarea
              id="description"
              placeholder="Brief description of your organization"
              rows={3}
              className={fieldState.error ? "border-destructive" : ""}
              {...field}
            />
          )}
        />
        {form.formState.errors.description && (
          <p className="text-sm text-destructive">
            {form.formState.errors.description.message}
          </p>
        )}
      </div>

      <div name="logo" className="space-y-2">
        <Label>Organization Logo</Label>
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16">
            <AvatarImage src={logoUrl} />
            <AvatarFallback className="text-xl">
              {watch("name")?.charAt(0) || "O"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <FileUpload
              accept={{ "image/*": [".png", ".jpg", ".jpeg", ".svg"] }}
              multiple={false}
              maxFiles={1}
              onUpload={handleLogoUpload}
              dropzoneText="Drop logo here or click to upload"
              buttonText="Upload Logo"
              showPreview={false}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Recommended: 256x256px, PNG or SVG format
            </p>
          </div>
        </div>
      </div>

      {/* Contact Information Fields */}
      <div name="website" className="space-y-2">
        <Label htmlFor="website">Website</Label>
        <Controller
          name="website"
          control={control}
          render={({ field, fieldState }) => (
            <Input
              id="website"
              placeholder="https://www.example.com"
              leftIcon={Globe}
              error={fieldState.error?.message}
              {...field}
            />
          )}
        />
      </div>

      <div name="email" className="space-y-2">
        <Label htmlFor="email">Contact Email</Label>
        <Controller
          name="email"
          control={control}
          render={({ field, fieldState }) => (
            <Input
              id="email"
              type="email"
              placeholder="contact@example.com"
              leftIcon={Mail}
              error={fieldState.error?.message}
              {...field}
            />
          )}
        />
      </div>

      <div name="phone" className="space-y-2">
        <Label htmlFor="phone">Phone Number</Label>
        <Controller
          name="phone"
          control={control}
          render={({ field, fieldState }) => (
            <Input
              id="phone"
              placeholder="+1 (555) 123-4567"
              leftIcon={Phone}
              error={fieldState.error?.message}
              {...field}
            />
          )}
        />
      </div>

      {/* Address Fields */}
      <div name="address" className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <Label htmlFor="street">Street Address</Label>
            <Controller
              name="address.street"
              control={control}
              render={({ field }) => (
                <Input
                  id="street"
                  placeholder="123 Main Street"
                  leftIcon={MapPin}
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="city">City</Label>
            <Controller
              name="address.city"
              control={control}
              render={({ field }) => (
                <Input
                  id="city"
                  placeholder="City"
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="state">State/Province</Label>
            <Controller
              name="address.state"
              control={control}
              render={({ field }) => (
                <Input
                  id="state"
                  placeholder="State or Province"
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="postalCode">Postal Code</Label>
            <Controller
              name="address.postalCode"
              control={control}
              render={({ field }) => (
                <Input
                  id="postalCode"
                  placeholder="12345"
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="country">Country</Label>
            <Controller
              name="address.country"
              control={control}
              render={({ field }) => (
                <Input
                  id="country"
                  placeholder="Country"
                  {...field}
                />
              )}
            />
          </div>
        </div>
      </div>

      {/* Business Details Fields */}
      <div name="businessDetails" className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="industry">Industry</Label>
            <Controller
              name="businessDetails.industry"
              control={control}
              render={({ field }) => (
                <Input
                  id="industry"
                  placeholder="e.g., Technology, Retail, Manufacturing"
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="size">Company Size</Label>
            <Controller
              name="businessDetails.size"
              control={control}
              render={({ field }) => (
                <select
                  id="size"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  {...field}
                >
                  <option value="">Select size</option>
                  <option value="1-10">1-10 employees</option>
                  <option value="11-50">11-50 employees</option>
                  <option value="51-200">51-200 employees</option>
                  <option value="201-1000">201-1000 employees</option>
                  <option value="1000+">1000+ employees</option>
                </select>
              )}
            />
          </div>
          <div>
            <Label htmlFor="taxId">Tax ID</Label>
            <Controller
              name="businessDetails.taxId"
              control={control}
              render={({ field }) => (
                <Input
                  id="taxId"
                  placeholder="Tax identification number"
                  {...field}
                />
              )}
            />
          </div>
          <div>
            <Label htmlFor="founded">Year Founded</Label>
            <Controller
              name="businessDetails.founded"
              control={control}
              render={({ field }) => (
                <Input
                  id="founded"
                  placeholder="2020"
                  maxLength={4}
                  {...field}
                />
              )}
            />
          </div>
        </div>
      </div>
    </>
  )
}