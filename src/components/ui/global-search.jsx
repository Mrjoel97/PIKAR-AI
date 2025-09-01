import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Command, File, User, Calendar, Settings } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { createPageUrl } from '@/utils';

const SEARCH_CATEGORIES = {
    pages: { icon: File, label: 'Pages', color: 'blue' },
    agents: { icon: User, label: 'Agents', color: 'green' },
    initiatives: { icon: Calendar, label: 'Initiatives', color: 'purple' },
    settings: { icon: Settings, label: 'Settings', color: 'gray' }
};

const SEARCH_ITEMS = [
    // Pages
    { id: 'dashboard', title: 'Dashboard', category: 'pages', url: createPageUrl('Dashboard'), description: 'Main overview and metrics' },
    { id: 'transformation', title: 'Transformation Hub', category: 'pages', url: createPageUrl('TransformationHub'), description: 'Business transformation center' },
    { id: 'analytics', title: 'Performance Analytics', category: 'pages', url: createPageUrl('PerformanceAnalytics'), description: 'Performance metrics and insights' },
    { id: 'resources', title: 'Resource Management', category: 'pages', url: createPageUrl('ResourceManagement'), description: 'Manage resources and costs' },
    { id: 'orchestration', title: 'Agent Orchestration', category: 'pages', url: createPageUrl('Orchestrate'), description: 'Coordinate AI agents' },
    { id: 'audit', title: 'Audit Trail', category: 'pages', url: createPageUrl('AuditTrail'), description: 'System activity logs' },
    { id: 'quality', title: 'Quality Management', category: 'pages', url: createPageUrl('QualityManagement'), description: 'ISO 9001 compliance' },
    { id: 'completion', title: 'Platform Completion Status', category: 'pages', url: createPageUrl('PlatformCompletionStatus'), description: 'Implementation progress' },

    // AI Agents
    { id: 'strategic', title: 'Strategic Planning Agent', category: 'agents', url: createPageUrl('StrategicPlanning'), description: 'SWOT, PESTEL, competitive analysis' },
    { id: 'content', title: 'Content Creation Agent', category: 'agents', url: createPageUrl('ContentCreation'), description: 'Generate marketing content' },
    { id: 'support', title: 'Customer Support Agent', category: 'agents', url: createPageUrl('CustomerSupport'), description: 'AI-powered support chat' },
    { id: 'sales', title: 'Sales Intelligence Agent', category: 'agents', url: createPageUrl('SalesIntelligence'), description: 'Lead scoring and analysis' },
    { id: 'data', title: 'Data Analysis Agent', category: 'agents', url: createPageUrl('DataAnalysis'), description: 'Data insights and reporting' },
    { id: 'marketing', title: 'Marketing Automation Agent', category: 'agents', url: createPageUrl('MarketingAutomation'), description: 'Campaign automation' },
    { id: 'financial', title: 'Financial Analysis Agent', category: 'agents', url: createPageUrl('FinancialAnalysis'), description: 'Financial forecasting' },
    { id: 'hr', title: 'HR & Recruitment Agent', category: 'agents', url: createPageUrl('HRRecruitment'), description: 'Resume screening and analysis' },
    { id: 'compliance', title: 'Compliance & Risk Agent', category: 'agents', url: createPageUrl('ComplianceRisk'), description: 'Compliance monitoring' },
    { id: 'operations', title: 'Operations Optimization Agent', category: 'agents', url: createPageUrl('OperationsOptimization'), description: 'Process optimization' },
    { id: 'custom', title: 'Custom Agents', category: 'agents', url: createPageUrl('CustomAgents'), description: 'Create custom AI agents' },

    // Settings
    { id: 'settings', title: 'Settings', category: 'settings', url: createPageUrl('Settings'), description: 'App configuration and preferences' }
];

export default function GlobalSearch({ isOpen, onClose }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [recentSearches, setRecentSearches] = useState([]);
    const inputRef = useRef(null);
    const resultsRef = useRef(null);

    const handleItemClick = useCallback((item) => {
        // Add to recent searches
        setRecentSearches(prev => {
            const filtered = prev.filter(search => search.id !== item.id);
            return [item, ...filtered].slice(0, 5);
        });

        // Navigate to the item
        window.location.href = item.url;
        onClose();
    }, [onClose]);

    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus();
            setQuery('');
            setSelectedIndex(0);
        }
    }, [isOpen]);

    useEffect(() => {
        if (query.trim()) {
            const filtered = SEARCH_ITEMS.filter(item =>
                item.title.toLowerCase().includes(query.toLowerCase()) ||
                item.description.toLowerCase().includes(query.toLowerCase())
            );
            setResults(filtered);
            setSelectedIndex(0);
        } else {
            setResults(recentSearches.length > 0 ? recentSearches : SEARCH_ITEMS.slice(0, 8));
        }
    }, [query, recentSearches]);

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!isOpen) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setSelectedIndex(prev => (prev + 1) % results.length);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    setSelectedIndex(prev => (prev - 1 + results.length) % results.length);
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (results[selectedIndex]) {
                        handleItemClick(results[selectedIndex]);
                    }
                    break;
                case 'Escape':
                    onClose();
                    break;
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, results, selectedIndex, handleItemClick, onClose]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-start justify-center pt-[20vh]">
            <div className="bg-white dark:bg-gray-900 rounded-lg shadow-2xl w-full max-w-2xl mx-4 max-h-[60vh] flex flex-col">
                {/* Search Header */}
                <div className="flex items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700">
                    <Search className="w-5 h-5 text-gray-400" />
                    <Input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search pages, agents, or features..."
                        className="border-none focus:ring-0 text-lg"
                    />
                    <div className="flex items-center gap-1 text-sm text-gray-400">
                        <Command className="w-4 h-4" />
                        <span>K</span>
                    </div>
                </div>

                {/* Search Results */}
                <div ref={resultsRef} className="flex-1 overflow-y-auto p-2">
                    {query.trim() === '' && recentSearches.length > 0 && (
                        <div className="px-3 py-2">
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Recent</h3>
                        </div>
                    )}
                    
                    <div className="space-y-1">
                        {results.map((item, index) => {
                            const category = SEARCH_CATEGORIES[item.category];
                            const IconComponent = category.icon;
                            
                            return (
                                <button
                                    key={item.id}
                                    onClick={() => handleItemClick(item)}
                                    className={`
                                        w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors
                                        ${index === selectedIndex 
                                            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700' 
                                            : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                                        }
                                    `}
                                >
                                    <div className={`p-2 rounded-lg bg-${category.color}-100 dark:bg-${category.color}-900/30`}>
                                        <IconComponent className={`w-4 h-4 text-${category.color}-600 dark:text-${category.color}-400`} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-medium text-gray-900 dark:text-white truncate">
                                                {item.title}
                                            </span>
                                            <Badge 
                                                variant="outline" 
                                                className={`text-xs text-${category.color}-600 border-${category.color}-200`}
                                            >
                                                {category.label}
                                            </Badge>
                                        </div>
                                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                                            {item.description}
                                        </p>
                                    </div>
                                </button>
                            );
                        })}
                    </div>

                    {results.length === 0 && query.trim() && (
                        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p>No results found for "{query}"</p>
                            <p className="text-sm mt-1">Try different keywords or browse categories</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-3 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-1">
                            <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">↑↓</kbd>
                            <span>Navigate</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">↵</kbd>
                            <span>Select</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <kbd className="px-2 py-1 bg-gray-100 rounded text-xs">Esc</kbd>
                            <span>Close</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}