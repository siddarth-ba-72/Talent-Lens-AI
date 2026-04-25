import { useState, useCallback } from 'react'
import { Upload, FileText, X, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { ALLOWED_FILE_TYPES, ALLOWED_MIME_TYPES, MAX_FILE_SIZE_BYTES } from '@/utils/constants'
import { formatFileSize } from '@/utils/formatters'

interface JdFileUploadProps {
  value: File | null
  onChange: (file: File | null) => void
  error?: string
}

export function JdFileUpload({ value, onChange, error }: JdFileUploadProps) {
  const [dragging, setDragging] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)

  const validate = (file: File): string | null => {
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return `Unsupported file type. Please use ${ALLOWED_FILE_TYPES.join(', ')}`
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      return `File is too large. Maximum size is 5 MB.`
    }
    return null
  }

  const handleFile = useCallback((file: File) => {
    const err = validate(file)
    if (err) {
      setFileError(err)
      return
    }
    setFileError(null)
    onChange(file)
  }, [onChange])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  const displayError = fileError ?? error

  if (value) {
    return (
      <div className="flex items-center gap-3 rounded-lg border-2 border-primary/30 bg-primary/5 px-4 py-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
          <FileText className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{value.name}</p>
          <p className="text-xs text-muted-foreground">{formatFileSize(value.size)}</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={() => onChange(null)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <label
        className={cn(
          'flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors',
          dragging
            ? 'border-primary bg-primary/5'
            : 'border-border hover:border-primary/50 hover:bg-muted/50'
        )}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <Upload className={cn('h-8 w-8 mb-3 transition-colors', dragging ? 'text-primary' : 'text-muted-foreground')} />
        <p className="text-sm font-medium mb-1">
          {dragging ? 'Drop to upload' : 'Drag & drop or click to browse'}
        </p>
        <p className="text-xs text-muted-foreground">
          Supports .txt, .pdf, .docx — max 5 MB
        </p>
        <input
          type="file"
          accept=".txt,.pdf,.docx"
          onChange={handleInputChange}
          className="sr-only"
        />
      </label>
      {displayError && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {displayError}
        </div>
      )}
    </div>
  )
}
