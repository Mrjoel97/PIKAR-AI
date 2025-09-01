
import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { AuditLog } from '@/api/entities';
import { Shield, Search, Filter, Bot, User, CheckCircle, XCircle } from 'lucide-react';
import { toast, Toaster } from 'sonner';

export default function AuditTrail() {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [filters, setFilters] = useState({
        action_type: 'all',
        risk_level: 'all',
        user: 'all',
    });

    useEffect(() => {
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        setIsLoading(true);
        try {
            const fetchedLogs = await AuditLog.list('-created_date', 200);
            setLogs(fetchedLogs);
        } catch (error) {
            console.error("Failed to fetch audit logs:", error);
            toast.error("Failed to load audit trail.");
        } finally {
            setIsLoading(false);
        }
    };
    
    const uniqueUsers = useMemo(() => [...new Set(logs.map(log => log.created_by))], [logs]);

    const filteredLogs = useMemo(() => {
        return logs.filter(log => {
            const searchMatch = log.action_details?.prompt?.toLowerCase().includes(searchQuery.toLowerCase()) || 
                                log.created_by?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                                log.ip_address?.includes(searchQuery);
            const typeMatch = filters.action_type === 'all' || log.action_type === filters.action_type;
            const riskMatch = filters.risk_level === 'all' || log.risk_level === filters.risk_level;
            const userMatch = filters.user === 'all' || log.created_by === filters.user;
            return searchMatch && typeMatch && riskMatch && userMatch;
        });
    }, [logs, searchQuery, filters]);

    const getRiskColor = (level) => {
        switch (level) {
            case 'high':
                return 'bg-red-100 text-red-800';
            case 'medium':
                return 'bg-yellow-100 text-yellow-800';
            case 'low':
                return 'bg-green-100 text-green-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <Toaster richColors />
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold flex items-center gap-3">
                    <Shield className="w-8 h-8 text-blue-600" />
                    Audit Trail
                </h1>
                <p className="text-lg text-gray-600 mt-1">
                    Monitor all critical activities and system events across the platform.
                </p>
            </div>

            {/* Filter & Search Card */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2"><Filter /> Filters</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col md:flex-row gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <Input 
                            placeholder="Search by user, IP, or details..."
                            className="pl-10"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    {/* Select components for filters */}
                    <Select onValueChange={(value) => setFilters(prev => ({ ...prev, action_type: value }))} value={filters.action_type}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Action Type" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Action Types</SelectItem>
                            <SelectItem value="BOT_INTERACTION">Bot Interaction</SelectItem>
                            <SelectItem value="USER_LOGIN">User Login</SelectItem>
                            <SelectItem value="DATA_ACCESS">Data Access</SelectItem>
                            {/* Add more action types as needed */}
                        </SelectContent>
                    </Select>
                    <Select onValueChange={(value) => setFilters(prev => ({ ...prev, risk_level: value }))} value={filters.risk_level}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Risk Level" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Risk Levels</SelectItem>
                            <SelectItem value="low">Low</SelectItem>
                            <SelectItem value="medium">Medium</SelectItem>
                            <SelectItem value="high">High</SelectItem>
                        </SelectContent>
                    </Select>
                    <Select onValueChange={(value) => setFilters(prev => ({ ...prev, user: value }))} value={filters.user}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="User" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All Users</SelectItem>
                            {uniqueUsers.map(user => (
                                <SelectItem key={user} value={user}>{user}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </CardContent>
            </Card>

            {/* Logs Table */}
            <Card>
                <CardHeader>
                    <CardTitle>Activity Logs</CardTitle>
                    <CardDescription>{filteredLogs.length} events found.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="border rounded-lg overflow-x-auto">
                        <table className="w-full min-w-[700px] text-sm">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="p-3 text-left">Timestamp</th>
                                    <th className="p-3 text-left">Action</th>
                                    <th className="p-3 text-left">User / Agent</th>
                                    <th className="p-3 text-left">Details</th>
                                    <th className="p-3 text-left">Status</th>
                                    <th className="p-3 text-left">Risk</th>
                                </tr>
                            </thead>
                            <tbody>
                                {isLoading ? (
                                    <tr><td colSpan="6" className="text-center p-8">Loading logs...</td></tr>
                                ) : filteredLogs.map(log => (
                                    <tr key={log.id} className="border-b last:border-b-0 hover:bg-gray-50">
                                        <td className="p-3 whitespace-nowrap">{new Date(log.created_date).toLocaleString()}</td>
                                        <td className="p-3">{log.action_type}</td>
                                        <td className="p-3">{log.created_by || log.agent_name || 'N/A'}</td>
                                        <td className="p-3 max-w-xs truncate">{log.action_details ? JSON.stringify(log.action_details) : 'N/A'}</td>
                                        <td className="p-3">
                                            {log.success ? <CheckCircle className="w-5 h-5 text-green-500" /> : <XCircle className="w-5 h-5 text-red-500" />}
                                        </td>
                                        <td className="p-3">
                                            <Badge className={getRiskColor(log.risk_level)}>{log.risk_level}</Badge>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {filteredLogs.length === 0 && !isLoading && (
                            <div className="text-center p-12 text-gray-500">No logs match your criteria.</div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
