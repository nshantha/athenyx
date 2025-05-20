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
    <div className="space-y-4 py-4">
      <div className="px-4 py-2 font-medium text-lg text-primary border-b border-border pb-2">
        Repository Management
      </div>

      {/* Active Repository */}
      {activeRepository && (
        <div className="px-4">
          <div className="mb-2 font-semibold text-primary">Active Repository</div>
          <div className="rounded-md bg-primary-foreground/10 p-3 border border-border/50">
            <div className="font-medium">{activeRepository.service_name}</div>
            <div className="text-xs text-muted-foreground break-all">
              {activeRepository.url}
            </div>
            {activeRepository.description && (
              <div className="mt-1 text-xs">{activeRepository.description}</div>
            )}
            {activeRepository.last_indexed && (
              <div className="mt-1 text-xs text-muted-foreground">
                <span className="text-green-500">✓</span> Indexed: {activeRepository.last_indexed}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Repository List */}
      <div className="px-4 mt-6">
        <div className="font-semibold text-primary mb-2">Select Repository</div>
        <div className="space-y-1 border border-border/50 rounded-md p-2">
          {repositories.map((repo) => (
            <Button
              key={repo.url}
              variant={repo.url === activeRepository?.url ? "secondary" : "ghost"}
              className="w-full justify-start text-left"
              onClick={() => setActiveRepository(repo.url)}
              disabled={isLoading || repo.url === activeRepository?.url}
            >
              <div className="truncate">
                <div>{repo.service_name}</div>
                {repo.url === activeRepository?.url && (
                  <div className="text-xs text-muted-foreground">Active</div>
                )}
              </div>
            </Button>
          ))}
        </div>
      </div>

      {/* Add Repository Button */}
      <div className="px-4 mt-4">
        <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
          <DialogTrigger asChild>
            <Button className="w-full" variant="outline">
              Add New Repository
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Repository</DialogTitle>
              <DialogDescription>
                Add a Git repository to be indexed and queried.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddRepository}>
              <div className="space-y-4 py-2">
                <div className="space-y-2">
                  <Label htmlFor="url">Repository URL *</Label>
                  <Input
                    id="url"
                    placeholder="https://github.com/username/repository.git"
                    value={newRepoUrl}
                    onChange={(e) => setNewRepoUrl(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="branch">Branch (optional)</Label>
                  <Input
                    id="branch"
                    placeholder="main"
                    value={newRepoBranch}
                    onChange={(e) => setNewRepoBranch(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="Description of this repository"
                    value={newRepoDesc}
                    onChange={(e) => setNewRepoDesc(e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter className="mt-4">
                <Button type="submit" disabled={isLoading || !newRepoUrl}>
                  Add Repository
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Ingestion Status */}
      {Object.keys(ingestingRepositories).length > 0 && (
        <div className="px-4 mt-6">
          <div className="font-semibold text-primary mb-2">Ingestion Status</div>
          <div className="space-y-2 border border-border/50 rounded-md p-2">
            {Object.entries(ingestingRepositories).map(([url, status]) => (
              <div key={url} className="rounded-md bg-amber-950/20 p-3 border border-amber-500/20">
                <div className="font-medium text-amber-500">{status.serviceName}</div>
                <div className="mt-1">
                  {status.indexed ? (
                    <div className="text-xs text-green-500">✓ Indexed</div>
                  ) : (
                    <>
                      <div className="h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 rounded-full"
                          style={{ width: `${status.progress}%` }}
                        />
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Elapsed: {status.elapsed}
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