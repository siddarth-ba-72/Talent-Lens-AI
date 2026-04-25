import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, FileText, Type, Sparkles, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { JdFileUpload } from '@/components/search/JdFileUpload'
import { ParsedJdSummary } from '@/components/search/ParsedJdSummary'
import { PlatformSelector } from '@/components/search/PlatformSelector'
import { createSearch, triggerSourcing } from '@/api/searchApi'
import { useUiStore } from '@/stores/uiStore'
import type { Search as SearchType, Platform } from '@/types/search'
import { MIN_JD_LENGTH } from '@/utils/constants'
import { cn } from '@/lib/utils'

type InputMode = 'text' | 'file'

export default function NewSearchPage() {
  const navigate = useNavigate()
  const { addToast } = useUiStore()

  const [inputMode, setInputMode] = useState<InputMode>('text')
  const [jdText, setJdText] = useState('')
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [platforms, setPlatforms] = useState<Platform[]>(['GITHUB', 'STACKOVERFLOW'])
  const [createdSearch, setCreatedSearch] = useState<SearchType | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [platformError, setPlatformError] = useState<string | null>(null)

  const analysisMutation = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      if (inputMode === 'text') {
        formData.append('jdText', jdText)
      } else if (jdFile) {
        formData.append('jdFile', jdFile)
      }
      return createSearch(formData)
    },
    onSuccess: (search) => {
      setCreatedSearch(search)
      addToast({ type: 'success', title: 'JD analysed!', description: 'Review the parsed results below.' })
    },
    onError: () => {
      addToast({ type: 'error', title: 'Analysis failed', description: 'Please check your input and try again.' })
    },
  })

  const sourcingMutation = useMutation({
    mutationFn: async () => {
      if (!createdSearch) throw new Error('No search created')
      return triggerSourcing(createdSearch.id, { platforms })
    },
    onSuccess: () => {
      addToast({ type: 'success', title: 'Sourcing started!', description: 'We\'re finding candidates for you.' })
      navigate(`/searches/${createdSearch!.id}`)
    },
    onError: () => {
      addToast({ type: 'error', title: 'Failed to start sourcing', description: 'Please try again.' })
    },
  })

  const handleAnalyse = () => {
    setValidationError(null)
    if (inputMode === 'text' && jdText.trim().length < MIN_JD_LENGTH) {
      setValidationError(`Please enter at least ${MIN_JD_LENGTH} characters.`)
      return
    }
    if (inputMode === 'file' && !jdFile) {
      setValidationError('Please upload a file.')
      return
    }
    analysisMutation.mutate()
  }

  const handleSource = () => {
    setPlatformError(null)
    if (platforms.length === 0) {
      setPlatformError('Please select at least one platform.')
      return
    }
    sourcingMutation.mutate()
  }

  const handleEditJd = () => {
    setCreatedSearch(null)
    analysisMutation.reset()
  }

  return (
    <div className="container mx-auto py-8 max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">New Search</h1>
          <p className="text-muted-foreground">Provide a job description to find matching candidates</p>
        </div>
      </div>

      {/* Step 1: JD Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</span>
            Job Description
          </CardTitle>
          <CardDescription>Paste the JD text or upload a document</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Mode toggle */}
          {!createdSearch && (
            <>
              <div className="flex rounded-lg border p-1 w-fit gap-1">
                <button
                  onClick={() => { setInputMode('text'); setJdFile(null) }}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                    inputMode === 'text' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <Type className="h-3.5 w-3.5" /> Paste text
                </button>
                <button
                  onClick={() => { setInputMode('file'); setJdText('') }}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-4 py-1.5 text-sm font-medium transition-colors',
                    inputMode === 'file' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <FileText className="h-3.5 w-3.5" /> Upload file
                </button>
              </div>

              {inputMode === 'text' ? (
                <div className="space-y-2">
                  <Textarea
                    placeholder="Paste the full job description here…"
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    className="min-h-[200px] text-sm leading-relaxed"
                  />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{jdText.length < MIN_JD_LENGTH ? `${MIN_JD_LENGTH - jdText.length} more characters needed` : '✓ Minimum length met'}</span>
                    <span>{jdText.length} chars</span>
                  </div>
                </div>
              ) : (
                <JdFileUpload value={jdFile} onChange={setJdFile} error={validationError ?? undefined} />
              )}

              {validationError && inputMode === 'text' && (
                <p className="text-xs text-destructive">{validationError}</p>
              )}

              <Button
                onClick={handleAnalyse}
                loading={analysisMutation.isPending}
                disabled={analysisMutation.isPending}
                className="gap-2"
              >
                <Sparkles className="h-4 w-4" />
                Analyse JD
              </Button>
            </>
          )}

          {/* Parsed JD result */}
          {createdSearch?.parsedJd && (
            <div className="space-y-3 animate-fade-in">
              <ParsedJdSummary parsedJd={createdSearch.parsedJd} title={createdSearch.title} />
              <Button variant="outline" size="sm" onClick={handleEditJd}>
                Edit JD
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Source candidates (only after parsing) */}
      {createdSearch && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">2</span>
              Source Candidates
            </CardTitle>
            <CardDescription>Choose platforms to search for matching candidates</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Label>Platforms</Label>
            <PlatformSelector value={platforms} onChange={setPlatforms} error={platformError ?? undefined} />
            <Button
              onClick={handleSource}
              loading={sourcingMutation.isPending}
              disabled={sourcingMutation.isPending}
              size="lg"
              className="gap-2 w-full sm:w-auto"
            >
              <Search className="h-4 w-4" />
              Source Candidates
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
