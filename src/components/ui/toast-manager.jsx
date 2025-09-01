import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircle, AlertTriangle, Info, X, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ToastContext = createContext();

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
};

export const ToastProvider = ({ children }) => {
    const [toasts, setToasts] = useState([]);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
    }, []);

    const addToast = useCallback((toast) => {
        const id = Date.now() + Math.random();
        const newToast = { id, ...toast };
        setToasts(prev => [...prev, newToast]);
        
        if (toast.duration !== 0) {
            setTimeout(() => {
                removeToast(id);
            }, toast.duration || 5000);
        }
        
        return id;
    }, [removeToast]);

    const toast = {
        success: (message, options = {}) => addToast({ type: 'success', message, ...options }),
        error: (message, options = {}) => addToast({ type: 'error', message, ...options }),
        warning: (message, options = {}) => addToast({ type: 'warning', message, ...options }),
        info: (message, options = {}) => addToast({ type: 'info', message, ...options }),
    };

    const getToastIcon = (type) => {
        switch (type) {
            case 'success': return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'error': return <XCircle className="w-5 h-5 text-red-500" />;
            case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
            case 'info': return <Info className="w-5 h-5 text-blue-500" />;
            default: return <Info className="w-5 h-5 text-blue-500" />;
        }
    };

    const getToastStyles = (type) => {
        switch (type) {
            case 'success': return 'border-green-200 bg-green-50 text-green-800';
            case 'error': return 'border-red-200 bg-red-50 text-red-800';
            case 'warning': return 'border-yellow-200 bg-yellow-50 text-yellow-800';
            case 'info': return 'border-blue-200 bg-blue-50 text-blue-800';
            default: return 'border-gray-200 bg-gray-50 text-gray-800';
        }
    };

    return (
        <ToastContext.Provider value={{ toast, addToast, removeToast }}>
            {children}
            <div className="fixed top-4 right-4 z-50 space-y-2">
                {toasts.map((toastItem) => (
                    <div
                        key={toastItem.id}
                        className={`
                            max-w-sm p-4 border rounded-lg shadow-lg transition-all duration-300
                            ${getToastStyles(toastItem.type)}
                        `}
                    >
                        <div className="flex items-start gap-3">
                            {getToastIcon(toastItem.type)}
                            <div className="flex-1">
                                <p className="font-medium">{toastItem.message}</p>
                                {toastItem.description && (
                                    <p className="text-sm opacity-75 mt-1">{toastItem.description}</p>
                                )}
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeToast(toastItem.id)}
                                className="p-1 h-auto"
                            >
                                <X className="w-4 h-4" />
                            </Button>
                        </div>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
};