import React, { useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { 
    BarChart3, 
    LineChart, 
    PieChart, 
    Table, 
    Plus, 
    Save, 
    Download, 
    Share, 
    Settings,
    Trash2,
    Move,
    Eye
} from 'lucide-react';
import { BarChart, Bar, LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart as RechartsPieChart, Pie, Cell } from 'recharts';
import { DndProvider, useDrag, useDrop } from '@hello-pangea/dnd';

const CHART_TYPES = [
    { type: 'bar', icon: BarChart3, label: 'Bar Chart', component: 'BarChart' },
    { type: 'line', icon: LineChart, label: 'Line Chart', component: 'LineChart' },
    { type: 'pie', icon: PieChart, label: 'Pie Chart', component: 'PieChart' },
    { type: 'table', icon: Table, label: 'Data Table', component: 'Table' }
];

const DATA_SOURCES = [
    { id: 'initiatives', label: 'Business Initiatives', fields: ['status', 'phase', 'category', 'priority'] },
    { id: 'usage', label: 'Usage Analytics', fields: ['agent_name', 'usage_type', 'session_duration', 'success_rate'] },
    { id: 'leads', label: 'Sales Leads', fields: ['lead_score', 'priority_level', 'industry', 'company_size'] },
    { id: 'content', label: 'Generated Content', fields: ['agent', 'format', 'tone', 'created_date'] }
];

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe'];

export default function ReportBuilder() {
    const [widgets, setWidgets] = useState([]);
    const [selectedDataSource, setSelectedDataSource] = useState('');
    const [selectedChartType, setSelectedChartType] = useState('');
    const [reportTitle, setReportTitle] = useState('Untitled Report');
    const [isPreview, setIsPreview] = useState(false);
    const [draggedWidget, setDraggedWidget] = useState(null);
    const canvasRef = useRef(null);

    const addWidget = () => {
        if (!selectedDataSource || !selectedChartType) return;

        const newWidget = {
            id: `widget-${Date.now()}`,
            type: selectedChartType,
            dataSource: selectedDataSource,
            title: `${selectedChartType.toUpperCase()} - ${DATA_SOURCES.find(ds => ds.id === selectedDataSource)?.label}`,
            x: 0,
            y: widgets.length * 220,
            width: 400,
            height: 200,
            config: {
                xField: DATA_SOURCES.find(ds => ds.id === selectedDataSource)?.fields[0] || '',
                yField: 'count',
                color: '#8884d8'
            }
        };

        setWidgets([...widgets, newWidget]);
        setSelectedDataSource('');
        setSelectedChartType('');
    };

    const updateWidget = (id, updates) => {
        setWidgets(widgets.map(widget => 
            widget.id === id ? { ...widget, ...updates } : widget
        ));
    };

    const deleteWidget = (id) => {
        setWidgets(widgets.filter(widget => widget.id !== id));
    };

    const generateMockData = (dataSource, field) => {
        const mockData = {
            initiatives: {
                status: [
                    { name: 'Active', value: 15 },
                    { name: 'Completed', value: 8 },
                    { name: 'On Hold', value: 3 }
                ],
                phase: [
                    { name: 'Discovery', value: 5 },
                    { name: 'Planning', value: 4 },
                    { name: 'Execution', value: 8 },
                    { name: 'Scale', value: 6 },
                    { name: 'Sustainability', value: 3 }
                ]
            },
            usage: {
                agent_name: [
                    { name: 'Strategic Planning', value: 28 },
                    { name: 'Data Analysis', value: 22 },
                    { name: 'Content Creation', value: 18 },
                    { name: 'Sales Intelligence', value: 15 }
                ],
                usage_type: [
                    { name: 'Analysis', value: 45 },
                    { name: 'Content Gen', value: 32 },
                    { name: 'File Upload', value: 23 }
                ]
            },
            leads: {
                lead_score: [
                    { name: '90-100', value: 12 },
                    { name: '80-89', value: 18 },
                    { name: '70-79', value: 25 },
                    { name: '60-69', value: 20 }
                ],
                industry: [
                    { name: 'Technology', value: 35 },
                    { name: 'Healthcare', value: 28 },
                    { name: 'Finance', value: 22 },
                    { name: 'Manufacturing', value: 15 }
                ]
            }
        };

        return mockData[dataSource]?.[field] || [];
    };

    const renderWidget = (widget) => {
        const data = generateMockData(widget.dataSource, widget.config.xField);
        
        switch (widget.type) {
            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height={widget.height - 60}>
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip />
                            <Bar dataKey="value" fill={widget.config.color} />
                        </BarChart>
                    </ResponsiveContainer>
                );
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height={widget.height - 60}>
                        <RechartsLineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip />
                            <Line type="monotone" dataKey="value" stroke={widget.config.color} />
                        </RechartsLineChart>
                    </ResponsiveContainer>
                );
            case 'pie':
                return (
                    <ResponsiveContainer width="100%" height={widget.height - 60}>
                        <RechartsPieChart>
                            <Pie
                                data={data}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={60}
                                fill={widget.config.color}
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip />
                        </RechartsPieChart>
                    </ResponsiveContainer>
                );
            case 'table':
                return (
                    <div className="overflow-auto h-full">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b">
                                    <th className="text-left p-2">Category</th>
                                    <th className="text-left p-2">Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.map((row, index) => (
                                    <tr key={index} className="border-b">
                                        <td className="p-2">{row.name}</td>
                                        <td className="p-2">{row.value}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                );
            default:
                return <div className="p-4 text-gray-500">Unsupported chart type</div>;
        }
    };

    const exportReport = () => {
        const reportData = {
            title: reportTitle,
            widgets: widgets,
            created: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${reportTitle.replace(/\s+/g, '_')}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <Input
                        value={reportTitle}
                        onChange={(e) => setReportTitle(e.target.value)}
                        className="text-2xl font-bold border-none px-0 shadow-none"
                    />
                    <p className="text-gray-600">Drag and drop report builder</p>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        onClick={() => setIsPreview(!isPreview)}
                    >
                        <Eye className="w-4 h-4 mr-2" />
                        {isPreview ? 'Edit' : 'Preview'}
                    </Button>
                    <Button variant="outline" onClick={exportReport}>
                        <Download className="w-4 h-4 mr-2" />
                        Export
                    </Button>
                    <Button>
                        <Save className="w-4 h-4 mr-2" />
                        Save Report
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Widget Palette */}
                {!isPreview && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Add Widget</CardTitle>
                            <CardDescription>Choose data source and chart type</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <label className="text-sm font-medium">Data Source</label>
                                <Select value={selectedDataSource} onValueChange={setSelectedDataSource}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select data source" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {DATA_SOURCES.map(source => (
                                            <SelectItem key={source.id} value={source.id}>
                                                {source.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div>
                                <label className="text-sm font-medium">Chart Type</label>
                                <div className="grid grid-cols-2 gap-2 mt-2">
                                    {CHART_TYPES.map(chart => (
                                        <button
                                            key={chart.type}
                                            onClick={() => setSelectedChartType(chart.type)}
                                            className={`p-3 border rounded-lg text-center transition-colors ${
                                                selectedChartType === chart.type 
                                                    ? 'bg-blue-50 border-blue-300' 
                                                    : 'hover:bg-gray-50'
                                            }`}
                                        >
                                            <chart.icon className="w-6 h-6 mx-auto mb-1" />
                                            <div className="text-xs">{chart.label}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <Button 
                                onClick={addWidget}
                                disabled={!selectedDataSource || !selectedChartType}
                                className="w-full"
                            >
                                <Plus className="w-4 h-4 mr-2" />
                                Add Widget
                            </Button>
                        </CardContent>
                    </Card>
                )}

                {/* Report Canvas */}
                <div className={`${isPreview ? 'lg:col-span-4' : 'lg:col-span-3'} space-y-6`}>
                    {widgets.length === 0 ? (
                        <Card className="h-64">
                            <CardContent className="flex items-center justify-center h-full text-center">
                                <div>
                                    <BarChart3 className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                                    <h3 className="font-medium text-gray-900">No widgets added</h3>
                                    <p className="text-sm text-gray-500">Add widgets from the panel to start building your report</p>
                                </div>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {widgets.map(widget => (
                                <Card key={widget.id}>
                                    <CardHeader className="pb-2">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-base">{widget.title}</CardTitle>
                                            {!isPreview && (
                                                <div className="flex gap-1">
                                                    <Button 
                                                        variant="ghost" 
                                                        size="sm"
                                                        onClick={() => {/* Open config modal */}}
                                                    >
                                                        <Settings className="w-4 h-4" />
                                                    </Button>
                                                    <Button 
                                                        variant="ghost" 
                                                        size="sm"
                                                        onClick={() => deleteWidget(widget.id)}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        {renderWidget(widget)}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}