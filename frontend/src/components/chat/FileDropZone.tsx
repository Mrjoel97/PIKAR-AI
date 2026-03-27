// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useCallback, useState } from 'react';
import { UploadCloud } from 'lucide-react';

interface FileDropZoneProps {
    onFileDrop: (file: File) => void;
    onFilesDrop?: (files: File[]) => void;
    children: React.ReactNode;
    disabled?: boolean;
}

export function FileDropZone({ onFileDrop, onFilesDrop, children, disabled }: FileDropZoneProps) {
    const [isDragActive, setIsDragActive] = useState(false);
    const [fileCount, setFileCount] = useState(0);

    const handleDragEnter = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (disabled) return;
        setIsDragActive(true);
        // Try to get file count from drag event
        if (e.dataTransfer.items) {
            setFileCount(e.dataTransfer.items.length);
        }
    }, [disabled]);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
        setFileCount(0);
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
        setFileCount(0);

        if (disabled) return;

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const files = Array.from(e.dataTransfer.files);
            
            // If onFilesDrop is provided, use it for all files
            if (onFilesDrop) {
                onFilesDrop(files);
            } else {
                // Fallback: call onFileDrop for each file
                files.forEach(file => onFileDrop(file));
            }
        }
    }, [disabled, onFileDrop, onFilesDrop]);

    return (
        <div
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            className="relative h-full w-full flex flex-col"
        >
            {isDragActive && (
                <div className="absolute inset-0 z-50 bg-indigo-50/90 dark:bg-slate-900/90 border-2 border-dashed border-indigo-500 rounded-xl flex flex-col items-center justify-center pointer-events-none animate-in fade-in duration-200">
                    <div className="p-4 bg-white dark:bg-slate-800 rounded-full shadow-xl mb-4">
                        <UploadCloud size={48} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="text-xl font-bold text-indigo-900 dark:text-indigo-100">
                        Drop {fileCount > 1 ? `${fileCount} files` : 'file'} to attach
                    </h3>
                    <p className="text-sm text-indigo-600 dark:text-indigo-300 mt-2">
                        Perfect for PDFs, Reports, and Data
                    </p>
                </div>
            )}
            {children}
        </div>
    );
}
