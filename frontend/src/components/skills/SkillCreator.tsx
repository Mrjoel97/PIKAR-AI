'use client'
import React, { useState } from 'react'
import { Sparkles, Code, Save, X, Plus, Terminal, Info, Loader2 } from 'lucide-react'

export function SkillCreator() {
    const [skillName, setSkillName] = useState('')
    const [description, setDescription] = useState('')
    const [code, setCode] = useState('def my_custom_skill(input_data: str):\n    # Write your logic here\n    return {"status": "success", "result": "processed " + input_data}')
    const [isSaving, setIsSaving] = useState(false)

    const handleSave = async () => {
        if (!skillName || !description) return
        setIsSaving(true)

        // In production, this would hit the FastAPI /skills endpoint
        try {
            await new Promise(resolve => setTimeout(resolve, 1500))
            alert('Skill registered successfully and added to agent inventory!')
            setSkillName('')
            setDescription('')
        } catch (err) {
            alert('Failed to save skill')
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 flex flex-col h-[700px] overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-slate-200 dark:border-slate-800 bg-indigo-600">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3 text-white">
                        <div className="p-2 bg-white/20 rounded-lg">
                            <Sparkles className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold">Custom Skill Creator</h2>
                            <p className="text-indigo-100 text-xs">Define new capabilities for your AI agents.</p>
                        </div>
                    </div>
                    <button className="text-white/60 hover:text-white transition">
                        <X className="w-5 h-5" />
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Configuration */}
                <div className="w-1/3 p-6 border-r border-slate-100 dark:border-slate-800 overflow-auto space-y-6">
                    <div>
                        <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Skill Name</label>
                        <input
                            type="text"
                            placeholder="e.g. analyze_market_sentiment"
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 transition font-mono text-sm"
                            value={skillName}
                            onChange={(e) => setSkillName(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Description</label>
                        <textarea
                            rows={4}
                            placeholder="Describe what this skill does and when the agent should use it..."
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm resize-none"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>

                    <div className="p-4 bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-900/30 rounded-xl">
                        <div className="flex gap-2 text-indigo-600 dark:text-indigo-400 mb-2">
                            <Info className="w-4 h-4 mt-0.5" />
                            <span className="text-xs font-bold uppercase tracking-wider">How it works</span>
                        </div>
                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                            Skills are Python functions. Your agents will automatically detect when to use this skill based on your description. Ensure your code returns a JSON-serializable dictionary.
                        </p>
                    </div>
                </div>

                {/* Right: Code Editor (Mock) */}
                <div className="flex-1 bg-slate-900 flex flex-col">
                    <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
                        <div className="flex items-center gap-2">
                            <Terminal className="w-4 h-4 text-emerald-400" />
                            <span className="text-xs font-mono text-slate-300">skill_definition.py</span>
                        </div>
                        <div className="flex gap-1">
                            <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                            <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                        </div>
                    </div>
                    <div className="flex-1 relative">
                        <textarea
                            className="w-full h-full p-6 bg-slate-900 text-emerald-400 font-mono text-sm outline-none resize-none selection:bg-indigo-500/30"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            spellCheck={false}
                        />
                    </div>
                </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex justify-between items-center">
                <div className="flex items-center gap-2 text-slate-400 text-xs">
                    <Code className="w-4 h-4" />
                    <span>Python 3.12 Runtime</span>
                </div>
                <button
                    onClick={handleSave}
                    disabled={isSaving || !skillName || !description}
                    className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-200 dark:shadow-none"
                >
                    {isSaving ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>Deploying...</span>
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />
                            <span>Save Skill</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    )
}
