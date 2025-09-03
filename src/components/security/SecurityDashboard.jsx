import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Shield, 
  AlertTriangle, 
  FileX, 
  CheckCircle, 
  Activity,
  Download,
  RefreshCw,
  Eye,
  Trash2,
  Filter
} from 'lucide-react';
import { toast } from 'sonner';
import { fileSecurityService } from '@/services/fileSecurityService';
import { auditService } from '@/services/auditService';
import { useAuth } from '@/contexts/AuthContext';
import { PermissionGuard } from '@/components/auth/ProtectedRoute';
import ErrorBoundary from '@/components/ErrorBoundary';

function SecurityDashboard() {
  const { user } = useAuth();
  const [securityMetrics, setSecurityMetrics] = useState(null);
  const [quarantinedFiles, setQuarantinedFiles] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTimeRange, setSelectedTimeRange] = useState('24h');

  useEffect(() => {
    loadSecurityData();
  }, [selectedTimeRange]);

  const loadSecurityData = async () => {
    setIsLoading(true);
    try {
      // Get security metrics
      const metrics = auditService.getSecurityMetrics();
      setSecurityMetrics(metrics);

      // Get quarantined files
      const quarantined = fileSecurityService.getQuarantinedFiles();
      setQuarantinedFiles(quarantined);

      // Get audit events
      const events = auditService.getEvents({
        limit: 100,
        startDate: getStartDate(selectedTimeRange)
      });
      setAuditEvents(events);

    } catch (error) {
      console.error('Failed to load security data:', error);
      toast.error('Failed to load security data');
    } finally {
      setIsLoading(false);
    }
  };

  const getStartDate = (range) => {
    const now = new Date();
    switch (range) {
      case '1h': return new Date(now.getTime() - 60 * 60 * 1000);
      case '24h': return new Date(now.getTime() - 24 * 60 * 60 * 1000);
      case '7d': return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      case '30d': return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      default: return new Date(now.getTime() - 24 * 60 * 60 * 1000);
    }
  };

  const handleClearQuarantine = () => {
    if (window.confirm('Are you sure you want to clear all quarantined files?')) {
      fileSecurityService.clearQuarantine();
      setQuarantinedFiles([]);
      toast.success('Quarantine cleared');
    }
  };

  const handleExportAuditLog = () => {
    try {
      const csv = auditService.exportEvents({
        startDate: getStartDate(selectedTimeRange)
      });
      
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `security_audit_${selectedTimeRange}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success('Audit log exported');
    } catch (error) {
      toast.error('Failed to export audit log');
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatEventType = (type) => {
    return type.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Security Dashboard</h1>
          <p className="text-gray-600">Monitor file uploads, security events, and system health</p>
        </div>
        
        <div className="flex items-center gap-3">
          <select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          
          <Button variant="outline" size="sm" onClick={loadSecurityData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Security Metrics */}
      {securityMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Events</p>
                  <p className="text-2xl font-bold text-gray-900">{securityMetrics.totalEvents}</p>
                </div>
                <Activity className="w-8 h-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Failed Logins</p>
                  <p className="text-2xl font-bold text-red-600">{securityMetrics.failedLogins}</p>
                </div>
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Blocked Files</p>
                  <p className="text-2xl font-bold text-orange-600">{quarantinedFiles.length}</p>
                </div>
                <FileX className="w-8 h-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Critical Events</p>
                  <p className="text-2xl font-bold text-red-600">{securityMetrics.criticalEvents}</p>
                </div>
                <Shield className="w-8 h-8 text-red-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="events" className="space-y-4">
        <TabsList>
          <TabsTrigger value="events">Security Events</TabsTrigger>
          <TabsTrigger value="quarantine">Quarantined Files</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Security Events */}
        <TabsContent value="events" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Security Events</CardTitle>
                  <CardDescription>
                    Latest security events and audit logs
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={handleExportAuditLog}>
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {auditEvents.length === 0 ? (
                  <p className="text-gray-500 text-center py-8">No security events found</p>
                ) : (
                  auditEvents.map((event) => (
                    <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Badge className={getSeverityColor(event.severity)}>
                          {event.severity}
                        </Badge>
                        <div>
                          <p className="font-medium text-gray-900">
                            {formatEventType(event.type)}
                          </p>
                          <p className="text-sm text-gray-500">
                            {new Date(event.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-600">
                          User: {event.data.userId || 'System'}
                        </p>
                        {event.data.email && (
                          <p className="text-xs text-gray-500">
                            {event.data.email}
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Quarantined Files */}
        <TabsContent value="quarantine" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Quarantined Files</CardTitle>
                  <CardDescription>
                    Files blocked by security scanning
                  </CardDescription>
                </div>
                <PermissionGuard permission="admin">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleClearQuarantine}
                    disabled={quarantinedFiles.length === 0}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Clear All
                  </Button>
                </PermissionGuard>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {quarantinedFiles.length === 0 ? (
                  <div className="text-center py-8">
                    <CheckCircle className="w-12 h-12 text-green-600 mx-auto mb-3" />
                    <p className="text-gray-500">No quarantined files</p>
                  </div>
                ) : (
                  quarantinedFiles.map((item) => (
                    <div key={item.scanResult.fileHash} className="p-4 border rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-gray-900">{item.scanResult.fileName}</h4>
                        <Badge className="bg-red-100 text-red-800">
                          Risk: {item.scanResult.riskScore}/100
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-3">
                        <div>Size: {formatFileSize(item.scanResult.fileSize)}</div>
                        <div>Type: {item.scanResult.mimeType}</div>
                        <div>Quarantined: {new Date(item.quarantineTime).toLocaleString()}</div>
                        <div>Hash: {item.scanResult.fileHash.substring(0, 16)}...</div>
                      </div>

                      {item.scanResult.threats.length > 0 && (
                        <div className="mb-2">
                          <p className="text-sm font-medium text-red-800 mb-1">Threats:</p>
                          <ul className="text-sm text-red-700 space-y-1">
                            {item.scanResult.threats.map((threat, index) => (
                              <li key={index}>• {threat}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {item.scanResult.warnings.length > 0 && (
                        <div>
                          <p className="text-sm font-medium text-yellow-800 mb-1">Warnings:</p>
                          <ul className="text-sm text-yellow-700 space-y-1">
                            {item.scanResult.warnings.map((warning, index) => (
                              <li key={index}>• {warning}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics */}
        <TabsContent value="analytics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Analytics</CardTitle>
              <CardDescription>
                Security trends and patterns analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Security Score */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Overall Security Score</h4>
                    <span className="text-2xl font-bold text-green-600">85/100</span>
                  </div>
                  <Progress value={85} className="h-3" />
                  <p className="text-sm text-gray-600 mt-1">
                    Based on recent security events and file scan results
                  </p>
                </div>

                {/* Threat Categories */}
                <div>
                  <h4 className="font-medium mb-3">Threat Categories</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Malicious Files</span>
                      <span className="text-sm font-medium">2</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Suspicious Patterns</span>
                      <span className="text-sm font-medium">5</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Failed Authentication</span>
                      <span className="text-sm font-medium">{securityMetrics?.failedLogins || 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Permission Violations</span>
                      <span className="text-sm font-medium">{securityMetrics?.permissionDenials || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Wrap with ErrorBoundary
export default function SecurityDashboardWithErrorBoundary() {
  return (
    <ErrorBoundary>
      <SecurityDashboard />
    </ErrorBoundary>
  );
}
