import React, { useState, useCallback, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  X, 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  FileText, 
  Image, 
  Music, 
  Video,
  Loader2,
  Eye,
  Download
} from 'lucide-react';
import { toast } from 'sonner';
import { fileSecurityService } from '@/services/fileSecurityService';
import { useAuth } from '@/contexts/AuthContext';
import { UploadFile } from '@/api/integrations';
import ErrorBoundary from '@/components/ErrorBoundary';

const FILE_ICONS = {
  image: Image,
  document: FileText,
  audio: Music,
  video: Video,
  default: FileText
};

function SecureFileUpload({
  purpose = 'general',
  maxFiles = 1,
  onUploadComplete,
  onUploadError,
  acceptedTypes = null,
  maxSize = null,
  className = '',
  disabled = false,
  showPreview = true,
  allowMultiple = false
}) {
  const { user } = useAuth();
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileSelect = useCallback(async (selectedFiles) => {
    if (disabled) return;

    const fileArray = Array.from(selectedFiles);
    
    // Check file count limit
    if (files.length + fileArray.length > maxFiles) {
      toast.error(`Maximum ${maxFiles} file(s) allowed`);
      return;
    }

    setIsScanning(true);

    try {
      const processedFiles = [];

      for (const file of fileArray) {
        // Create file object with metadata
        const fileObj = {
          id: `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'scanning',
          scanResult: null,
          uploadResult: null,
          progress: 0
        };

        processedFiles.push(fileObj);
        setFiles(prev => [...prev, fileObj]);

        // Perform security scan
        try {
          const scanResult = await fileSecurityService.scanFile(file, {
            purpose,
            userId: user?.id,
            deepScan: true
          });

          fileObj.scanResult = scanResult;
          fileObj.status = scanResult.allowed ? 'safe' : 'blocked';

          if (!scanResult.allowed) {
            toast.error(`File "${file.name}" blocked: ${scanResult.threats.join(', ')}`);
          } else if (scanResult.warnings.length > 0) {
            toast.warning(`File "${file.name}" has warnings: ${scanResult.warnings.join(', ')}`);
          } else {
            toast.success(`File "${file.name}" passed security scan`);
          }

        } catch (error) {
          fileObj.status = 'error';
          fileObj.error = error.message;
          toast.error(`Scan failed for "${file.name}": ${error.message}`);
        }

        // Update file state
        setFiles(prev => prev.map(f => f.id === fileObj.id ? fileObj : f));
      }

    } catch (error) {
      toast.error('File processing failed');
      console.error('File processing error:', error);
    } finally {
      setIsScanning(false);
    }
  }, [files, maxFiles, purpose, user?.id, disabled]);

  const handleUpload = async (fileObj) => {
    if (!fileObj.scanResult?.allowed) {
      toast.error('Cannot upload blocked file');
      return;
    }

    setIsUploading(true);
    fileObj.status = 'uploading';
    setFiles(prev => prev.map(f => f.id === fileObj.id ? f : f));

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        fileObj.progress = Math.min(fileObj.progress + 10, 90);
        setFiles(prev => prev.map(f => f.id === fileObj.id ? f : f));
      }, 200);

      // Upload file via Supabase storage helper
      const uploadResult = await UploadFile({ file: fileObj.file, pathPrefix: `uploads/${purpose}` })

      clearInterval(progressInterval);
      fileObj.progress = 100;
      fileObj.status = 'completed';
      fileObj.uploadResult = uploadResult;

      setFiles(prev => prev.map(f => f.id === fileObj.id ? f : f));

      toast.success(`File "${fileObj.name}" uploaded successfully`);
      
      if (onUploadComplete) {
        onUploadComplete(fileObj, uploadResult);
      }

    } catch (error) {
      fileObj.status = 'failed';
      fileObj.error = error.message;
      setFiles(prev => prev.map(f => f.id === fileObj.id ? f : f));

      toast.error(`Upload failed for "${fileObj.name}": ${error.message}`);
      
      if (onUploadError) {
        onUploadError(fileObj, error);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadAll = async () => {
    const safeFiles = files.filter(f => f.scanResult?.allowed && f.status === 'safe');
    
    for (const fileObj of safeFiles) {
      await handleUpload(fileObj);
    }
  };

  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (!disabled) {
      const droppedFiles = e.dataTransfer.files;
      handleFileSelect(droppedFiles);
    }
  };

  const getFileIcon = (fileType) => {
    if (fileType.startsWith('image/')) return FILE_ICONS.image;
    if (fileType.startsWith('audio/')) return FILE_ICONS.audio;
    if (fileType.startsWith('video/')) return FILE_ICONS.video;
    return FILE_ICONS.document;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'scanning': return 'bg-blue-100 text-blue-800';
      case 'safe': return 'bg-green-100 text-green-800';
      case 'blocked': return 'bg-red-100 text-red-800';
      case 'uploading': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-emerald-100 text-emerald-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'scanning': return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'safe': return <Shield className="w-4 h-4" />;
      case 'blocked': return <AlertTriangle className="w-4 h-4" />;
      case 'uploading': return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'failed': return <X className="w-4 h-4" />;
      default: return null;
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const safeFilesCount = files.filter(f => f.scanResult?.allowed).length;
  const blockedFilesCount = files.filter(f => f.status === 'blocked').length;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Upload Area */}
      <div
        className={`
          border-2 border-dashed rounded-lg p-6 text-center transition-colors
          ${isDragging ? 'border-emerald-500 bg-emerald-50' : 'border-gray-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:border-emerald-400'}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple={allowMultiple}
          accept={acceptedTypes}
          onChange={(e) => handleFileSelect(e.target.files)}
          disabled={disabled}
        />
        
        <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-600 mb-1">
          {isDragging ? 'Drop files here' : 'Click to upload or drag and drop'}
        </p>
        <p className="text-xs text-gray-400">
          Files will be scanned for security before upload
        </p>
        
        {/* Security Badge */}
        <div className="flex items-center justify-center gap-2 mt-3">
          <Shield className="w-4 h-4 text-emerald-600" />
          <span className="text-xs text-emerald-600 font-medium">
            Advanced Security Scanning
          </span>
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-gray-900">
              Files ({files.length})
            </h4>
            
            {safeFilesCount > 0 && (
              <Button
                size="sm"
                onClick={handleUploadAll}
                disabled={isUploading || isScanning}
                className="flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Upload All Safe Files ({safeFilesCount})
              </Button>
            )}
          </div>

          {files.map((fileObj) => {
            const FileIcon = getFileIcon(fileObj.type);
            
            return (
              <Card key={fileObj.id} className="p-4">
                <div className="flex items-center gap-3">
                  <FileIcon className="w-8 h-8 text-gray-500 flex-shrink-0" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {fileObj.name}
                      </p>
                      <Badge className={getStatusColor(fileObj.status)}>
                        <div className="flex items-center gap-1">
                          {getStatusIcon(fileObj.status)}
                          <span className="capitalize">{fileObj.status}</span>
                        </div>
                      </Badge>
                    </div>
                    
                    <p className="text-xs text-gray-500">
                      {formatFileSize(fileObj.size)} • {fileObj.type}
                    </p>
                    
                    {/* Progress Bar */}
                    {fileObj.status === 'uploading' && (
                      <Progress value={fileObj.progress} className="mt-2 h-2" />
                    )}
                    
                    {/* Scan Results */}
                    {fileObj.scanResult && (
                      <div className="mt-2 space-y-1">
                        {fileObj.scanResult.threats.length > 0 && (
                          <div className="text-xs text-red-600">
                            <strong>Threats:</strong> {fileObj.scanResult.threats.join(', ')}
                          </div>
                        )}
                        {fileObj.scanResult.warnings.length > 0 && (
                          <div className="text-xs text-yellow-600">
                            <strong>Warnings:</strong> {fileObj.scanResult.warnings.join(', ')}
                          </div>
                        )}
                        <div className="text-xs text-gray-500">
                          Risk Score: {fileObj.scanResult.riskScore}/100
                        </div>
                      </div>
                    )}
                    
                    {/* Error Message */}
                    {fileObj.error && (
                      <div className="mt-2 text-xs text-red-600">
                        <strong>Error:</strong> {fileObj.error}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {fileObj.status === 'safe' && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUpload(fileObj)}
                        disabled={isUploading}
                      >
                        <Upload className="w-4 h-4" />
                      </Button>
                    )}
                    
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeFile(fileObj.id)}
                      disabled={isUploading && fileObj.status === 'uploading'}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Summary */}
      {files.length > 0 && (
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>Total: {files.length}</span>
          {safeFilesCount > 0 && (
            <span className="text-green-600">Safe: {safeFilesCount}</span>
          )}
          {blockedFilesCount > 0 && (
            <span className="text-red-600">Blocked: {blockedFilesCount}</span>
          )}
        </div>
      )}
    </div>
  );
}

// Wrap with ErrorBoundary
export default function SecureFileUploadWithErrorBoundary(props) {
  return (
    <ErrorBoundary>
      <SecureFileUpload {...props} />
    </ErrorBoundary>
  );
}
