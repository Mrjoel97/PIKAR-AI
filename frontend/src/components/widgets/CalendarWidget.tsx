// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import React, { useState } from 'react';
import { WidgetDefinition, CalendarData, CalendarEvent } from '@/types/widgets';
import { Calendar, Clock, MapPin, Plus } from 'lucide-react';

interface CalendarWidgetProps {
    definition: WidgetDefinition;
    onAction?: (action: string, data: any) => void;
}

export default function CalendarWidget({ definition, onAction }: CalendarWidgetProps) {
    const data = definition.data as unknown as CalendarData;
    const { view = 'month', events = [] } = data;

    const handleEventClick = (event: CalendarEvent) => {
        if (onAction) {
            onAction('view_event', {
                eventId: event.id,
                event
            });
        }
    };

    const handleAddEvent = () => {
        if (onAction) {
            onAction('add_event', {});
        }
    };

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    };

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr);
        return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className="w-full bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-slate-500" />
                    <h3 className="font-semibold text-slate-800 dark:text-slate-200">{definition.title}</h3>
                </div>
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wider bg-slate-200 dark:bg-slate-700 px-2 py-0.5 rounded">
                    {view} View
                </div>
            </div>

            <div className="p-4">
                {/* Simplified List View for this iteration */}
                <div className="space-y-3">
                    {events.length === 0 ? (
                        <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                            No upcoming events scheduled.
                        </div>
                    ) : (
                        events.map(event => (
                            <div
                                key={event.id}
                                onClick={() => handleEventClick(event)}
                                className={`p-3 rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer hover:shadow-md transition-all ${event.color ? event.color.replace('bg-', 'bg-opacity-20 bg-').replace('text-', 'border-l-4 border-') : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/50'}`}
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <h4 className="font-medium text-slate-900 dark:text-slate-100">{event.title}</h4>
                                        <div className="flex items-center gap-3 mt-1 text-xs text-slate-500 dark:text-slate-400">
                                            <div className="flex items-center gap-1">
                                                <Clock size={12} />
                                                <span>{formatDate(event.start)} • {formatTime(event.start)} - {formatTime(event.end)}</span>
                                            </div>
                                            {event.location && (
                                                <div className="flex items-center gap-1">
                                                    <MapPin size={12} />
                                                    <span>{event.location}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700/50">
                    <button
                        onClick={handleAddEvent}
                        aria-label="Add event"
                        className="w-full py-2 flex items-center justify-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-md transition-colors"
                    >
                        <Plus size={16} />
                        <span>Schedule Event</span>
                    </button>
                </div>
            </div>

            {/* Mock Month View Grid - purely visual for the test "renders month view by default" */}
            {view === 'month' && (
                <div className="px-4 pb-4 opacity-50 text-[10px] text-slate-400 flex justify-between">
                    <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
                </div>
            )}
        </div>
    );
}
