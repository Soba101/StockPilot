"use client"

import * as React from "react"
import { useDropzone } from "react-dropzone"
import { cn } from "@/lib/utils"
import { Button } from "./button"
import { Badge } from "./badge"
import { Upload, File, X, AlertCircle, Check } from "lucide-react"

export interface FileUploadProps {
  accept?: Record<string, string[]>
  multiple?: boolean
  maxSize?: number // in bytes
  maxFiles?: number
  onUpload: (files: File[]) => Promise<void> | void
  onRemove?: (file: File) => void
  disabled?: boolean
  loading?: boolean
  className?: string
  dropzoneText?: string
  buttonText?: string
  showPreview?: boolean
  value?: File[]
}

export function FileUpload({
  accept = { "text/csv": [".csv"], "application/vnd.ms-excel": [".xls", ".xlsx"] },
  multiple = false,
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 1,
  onUpload,
  onRemove,
  disabled = false,
  loading = false,
  className,
  dropzoneText = "Drag & drop files here, or click to select",
  buttonText = "Select Files",
  showPreview = true,
  value = [],
}: FileUploadProps) {
  const [files, setFiles] = React.useState<File[]>(value)
  const [uploadProgress, setUploadProgress] = React.useState<Record<string, number>>({})
  const [errors, setErrors] = React.useState<string[]>([])

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragReject,
    fileRejections,
  } = useDropzone({
    accept,
    multiple,
    maxSize,
    maxFiles: multiple ? maxFiles : 1,
    disabled: disabled || loading,
    onDrop: async (acceptedFiles, rejectedFiles) => {
      // Handle rejected files
      const rejectionErrors = rejectedFiles.map(rejection => {
        const error = rejection.errors[0]
        return `${rejection.file.name}: ${error.message}`
      })
      setErrors(rejectionErrors)

      if (acceptedFiles.length > 0) {
        const newFiles = multiple ? [...files, ...acceptedFiles] : acceptedFiles
        setFiles(newFiles)
        
        try {
          await onUpload(acceptedFiles)
          setErrors([])
        } catch (error) {
          setErrors([`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`])
        }
      }
    },
  })

  const removeFile = (fileToRemove: File) => {
    const newFiles = files.filter(file => file !== fileToRemove)
    setFiles(newFiles)
    onRemove?.(fileToRemove)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }

  const getFileIcon = (file: File) => {
    if (file.type.includes("csv") || file.type.includes("excel")) {
      return File
    }
    return File
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          isDragActive && !isDragReject && "border-primary bg-primary/10",
          isDragReject && "border-destructive bg-destructive/10",
          disabled && "cursor-not-allowed opacity-50",
          "hover:border-primary hover:bg-primary/5"
        )}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className={cn(
            "p-4 rounded-full",
            isDragActive && !isDragReject && "bg-primary/20",
            isDragReject && "bg-destructive/20",
            !isDragActive && "bg-muted"
          )}>
            <Upload className={cn(
              "h-8 w-8",
              isDragActive && !isDragReject && "text-primary",
              isDragReject && "text-destructive",
              !isDragActive && "text-muted-foreground"
            )} />
          </div>
          
          <div className="space-y-2">
            <p className="text-lg font-medium">
              {isDragActive ? "Drop files here" : dropzoneText}
            </p>
            <p className="text-sm text-muted-foreground">
              {Object.values(accept).flat().join(", ")} up to {formatFileSize(maxSize)}
            </p>
          </div>
          
          <Button
            type="button"
            variant="outline"
            disabled={disabled || loading}
            loading={loading}
          >
            {buttonText}
          </Button>
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="space-y-2">
          {errors.map((error, index) => (
            <div key={index} className="flex items-center space-x-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          ))}
        </div>
      )}

      {/* File rejections */}
      {fileRejections.length > 0 && (
        <div className="space-y-2">
          {fileRejections.map(({ file, errors }, index) => (
            <div key={index} className="flex items-center space-x-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{file.name}: {errors[0].message}</span>
            </div>
          ))}
        </div>
      )}

      {/* File preview */}
      {showPreview && files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Uploaded Files</h4>
          <div className="space-y-2">
            {files.map((file, index) => {
              const FileIcon = getFileIcon(file)
              const progress = uploadProgress[file.name] || 100
              
              return (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <FileIcon className="h-5 w-5 text-muted-foreground" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {progress < 100 ? (
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-muted rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">{progress}%</span>
                      </div>
                    ) : (
                      <Badge variant="success" icon={Check}>
                        Uploaded
                      </Badge>
                    )}
                    
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => removeFile(file)}
                      disabled={loading}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}