'use client'
import React, { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'
import { Upload, FileText, Trash2, Loader2, Search, File } from 'lucide-react'

export function KnowledgeVault() {
  const [uploading, setUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [documents, setDocuments] = useState<any[]>([
    { id: '1', name: 'Business_Strategy_2025.pdf', size: '2.4MB', date: '2026-01-20' },
    { id: '2', name: 'Product_Roadmap_V2.md', size: '15KB', date: '2026-01-22' },
  ]) // Mock data for now
  const [userId, setUserId] = useState<string | null>(null)
  const supabase = createClient()

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) setUserId(data.user.id)
    })
  }, [supabase])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    
    setUploading(true)
    const file = e.target.files[0]
    const fileExt = file.name.split('.').pop()
    const filePath = `${userId}/${crypto.randomUUID()}.${fileExt}`

    try {
      // Note: Bucket must be created in Supabase console/migration first
      const { error: uploadError } = await supabase.storage
        .from('knowledge-vault')
        .upload(filePath, file)

      if (uploadError) throw uploadError
      
      // Add to list (in real app, this would be fetched from DB)
      setDocuments(prev => [{
        id: Math.random().toString(),
        name: file.name,
        size: `${(file.size / 1024 / 1024).toFixed(2)}MB`,
        date: new Date().toISOString().split('T')[0]
      }, ...prev])

      alert('Upload successful! Document is being processed for RAG.')
    } catch (error: any) {
      console.error('Upload error:', error)
      alert('Error uploading: ' + error.message + '. Make sure the "knowledge-vault" bucket exists.')
    } finally {
      setUploading(false)
    }
  }

  const deleteDocument = (id: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== id))
  }

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-3 text-slate-800 dark:text-slate-100">
            <FileText className="text-indigo-600 w-8 h-8" /> Knowledge Vault
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mt-1">Manage and search your business intelligence.</p>
        </div>
        <div className="flex gap-2">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
                <input 
                    type="text" 
                    placeholder="Search documents..." 
                    className="pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>
        </div>
      </div>
      
      {/* Upload Zone */}
      <div className="mb-8">
        <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-slate-300 dark:border-slate-700 border-dashed rounded-2xl cursor-pointer bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all group">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {uploading ? (
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 className="animate-spin text-indigo-600 w-10 h-10" />
                        <p className="text-sm font-medium text-slate-600">Processing file...</p>
                    </div>
                ) : (
                    <>
                        <div className="p-4 bg-indigo-50 dark:bg-indigo-900/20 rounded-full mb-3 group-hover:scale-110 transition-transform">
                            <Upload className="w-6 h-6 text-indigo-600" />
                        </div>
                        <p className="text-sm text-slate-600 dark:text-slate-300"><span className="font-semibold text-indigo-600">Click to upload</span> or drag and drop</p>
                        <p className="text-xs text-slate-400 mt-1">PDF, TXT, DOCX, Markdown (Max 10MB)</p>
                    </>
                )}
            </div>
            <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {/* Documents Table/List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Repository</h3>
            <span className="text-xs text-slate-400">{documents.length} files total</span>
        </div>

        <div className="grid gap-3">
            {documents.filter(doc => doc.name.toLowerCase().includes(searchQuery.toLowerCase())).map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-4 bg-white dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700 hover:shadow-md transition group">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-slate-100 dark:bg-slate-700 rounded-lg">
                            <File className="w-5 h-5 text-slate-500" />
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{doc.name}</p>
                            <p className="text-xs text-slate-400">{doc.size} • Uploaded on {doc.date}</p>
                        </div>
                    </div>
                    <button 
                        onClick={() => deleteDocument(doc.id)}
                        className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            ))}
            
            {documents.length === 0 && (
                <div className="text-center py-12 border border-dashed rounded-2xl">
                    <p className="text-slate-400 italic">No documents found in the vault.</p>
                </div>
            )}
        </div>
      </div>
    </div>
  )
}
