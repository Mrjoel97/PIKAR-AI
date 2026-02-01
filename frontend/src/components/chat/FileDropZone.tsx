import React, { useCallback, useState } from 'react';
import { UploadCloud } from 'lucide-react';

interface FileDropZoneProps {
    onFileDrop: (file: File) => void;
    children: React.ReactNode;
    disabled?: boolean;
}

export function FileDropZone({ onFileDrop, children, disabled }: FileDropZoneProps) {
    const [isDragActive, setIsDragActive] = useState(false);

    const handleDragEnter = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (disabled) return;
        setIsDragActive(true);
    }, [disabled]);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);
    }, []);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragActive(false);

        if (disabled) return;

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            onFileDrop(file);
        }
    }, [disabled, onFileDrop]);

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
                        Drop file to analyze
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
