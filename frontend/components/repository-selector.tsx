'use client'

import { useState } from 'react'
import { useRepository } from '@/lib/repository-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Repository } from '@/lib/api'

export function RepositorySelector() {
  const {
    repositories,
    activeRepository,
    ingestingRepositories,
    isLoading,
    setActiveRepository,
    addRepository
  } = useRepository()

  const [newRepoUrl, setNewRepoUrl] = useState('')
  const [newRepoBranch, setNewRepoBranch] = useState('')
  const [newRepoDesc, setNewRepoDesc] = useState('')
  const [addDialogOpen, setAddDialogOpen] = useState(false)

  const handleAddRepository = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newRepoUrl) return

    await addRepository({
      url: newRepoUrl,
      branch: newRepoBranch || undefined,
      description: newRepoDesc || undefined
    })

    // Reset form
    setNewRepoUrl('')
    setNewRepoBranch('')
    setNewRepoDesc('')
    setAddDialogOpen(false)
  }

  return (
    <div className="space-y-3 py-3"> {/* Reduced overall vertical spacing slightly */}
      <div className="px-3 pb-2 pt-1 text-base font-semibold text-primary border-b border-border/60"> {/* Adjusted title styling */}
        Repository Management
      </div>

      {/* Active Repository */}
      {activeRepository && (
        <div className="px-3 space-y-1.5"> {/* Consistent padding and small gap */}
          <div className="text-sm font-medium text-primary">Active Repository</div>
          <div className="rounded-lg bg-muted/80 p-3 border border-border shadow-sm"> {/* Enhanced background, border, shadow */}
            <div className="flex items-center justify-between">
              <div className="font-semibold text-primary-foreground">{activeRepository.service_name}</div>
              <span className="text-xs font-medium bg-green-600 text-white px-2 py-0.5 rounded-full">
                Active
              </span>
            </div>
            <div className="text-xs text-muted-foreground break-all mt-1">
              {activeRepository.url}
            </div>
            {activeRepository.description && (
              <div className="mt-1.5 text-xs text-muted-foreground">{activeRepository.description}</div>
            )}
            {activeRepository.last_indexed && (
              <div className="mt-1.5 text-xs text-green-600"> {/* Use a consistent green */}
                ✓ Indexed: {new Date(activeRepository.last_indexed).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Repository List */}
      <div className="px-3 mt-4 space-y-1.5"> {/* Consistent padding and gap */}
        <div className="text-sm font-medium text-primary mb-1">Select Repository</div>
        <div className="space-y-1 rounded-md border border-border bg-background p-1"> {/* Added bg-background for list container */}
          {repositories.map((repo) => {
            const isActive = repo.url === activeRepository?.url;
            return (
              <Button
                key={repo.url}
                variant={isActive ? "secondary" : "ghost"}
                className={`w-full justify-start text-left h-auto py-2 px-2.5 ${isActive ? 'shadow-sm' : ''}`}
                onClick={() => setActiveRepository(repo.url)}
                disabled={isLoading || isActive}
              >
                <div className="truncate flex-grow">
                  <div className={`font-medium ${isActive ? 'text-secondary-foreground' : 'text-primary'}`}>{repo.service_name}</div>
                  <div className={`text-xs ${isActive ? 'text-muted-foreground font-medium' : 'text-muted-foreground'}`}>
                    {repo.description || repo.url}
                  </div>
                </div>
                {isActive && (
                  <span className="ml-2 text-xs text-green-600 font-semibold">✓ Active</span>
                )}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Add Repository Button */}
      <div className="px-3 mt-3"> {/* Consistent padding */}
        <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
          <DialogTrigger asChild>
            <Button className="w-full" variant="outline">
              Add New Repository
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[480px]"> {/* Slightly wider dialog for better form layout */}
            <DialogHeader>
              <DialogTitle>Add New Repository</DialogTitle>
              <DialogDescription>
                Provide the Git repository URL and an optional branch and description.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddRepository} className="space-y-4 pt-2 pb-1"> {/* Added form specific spacing */}
              <div className="space-y-1.5">
                <Label htmlFor="url" className="text-sm font-medium">Repository URL *</Label>
                <Input
                  id="url"
                  placeholder="https://github.com/username/repository.git"
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  required
                  className="h-10" // Standard input height
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="branch" className="text-sm font-medium">Branch (optional)</Label>
                <Input
                  id="branch"
                  placeholder="main"
                  value={newRepoBranch}
                  onChange={(e) => setNewRepoBranch(e.target.value)}
                  className="h-10"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="description" className="text-sm font-medium">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="A brief description of this repository"
                  value={newRepoDesc}
                  onChange={(e) => setNewRepoDesc(e.target.value)}
                  rows={3}
                  className="text-sm" // Ensure textarea font size is consistent
                />
              </div>
              <DialogFooter className="pt-3"> {/* Added padding to footer */}
                <Button type="button" variant="ghost" onClick={() => setAddDialogOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={isLoading || !newRepoUrl}>
                  {isLoading ? 'Adding...' : 'Add Repository'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Ingestion Status */}
      {Object.keys(ingestingRepositories).length > 0 && (
        <div className="px-3 mt-4 space-y-1.5"> {/* Consistent padding and gap */}
          <div className="text-sm font-medium text-primary mb-1">Ingestion Status</div>
          <div className="space-y-2 rounded-md border border-border bg-background p-2"> {/* Added bg-background for list container */}
            {Object.entries(ingestingRepositories).map(([url, status]) => (
              <div key={url} className="rounded-md bg-amber-500/10 p-3 border border-amber-500/30 shadow-sm"> {/* Subtle amber bg and border */}
                <div className="font-semibold text-amber-700 dark:text-amber-400">{status.serviceName || url}</div> {/* Ensure serviceName or URL shown */}
                <div className="mt-1.5">
                  {status.indexed ? (
                    <div className="text-xs text-green-600">✓ Successfully Indexed</div>
                  ) : (
                    <>
                      <div className="h-2 w-full bg-muted rounded-full overflow-hidden my-1"> {/* Slightly thicker progress bar */}
                        <div
                          className="h-full bg-amber-500 rounded-full transition-all duration-300" // Added transition
                          style={{ width: `${status.progress}%` }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Progress: {status.progress}% {status.elapsed && `(${status.elapsed})`}
                      </div>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 