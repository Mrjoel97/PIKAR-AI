'use client'
import React, { useState } from 'react';
import { WidgetDefinition, KanbanData, Column, Card } from '@/types/widgets';
import { Plus, MoreHorizontal } from 'lucide-react';

interface KanbanWidgetProps {
    definition: WidgetDefinition;
    onAction?: (action: string, data: any) => void;
}

export default function KanbanWidget({ definition, onAction }: KanbanWidgetProps) {
    const data = definition.data as unknown as KanbanData;
    const { columns = [], cards = [] } = data;

    const handleCardClick = (card: Card) => {
        if (onAction) {
            onAction('view_card', {
                cardId: card.id,
                card
            });
        }
    };

    const handleAddCard = (columnId: string) => {
        if (onAction) {
            onAction('add_card', { columnId });
        }
    };

    const getColumnCards = (columnId: string) => {
        return cards.filter(c => c.columnId === columnId);
    };

    return (
        <div className="w-full h-full min-h-[400px] flex flex-col bg-slate-50 dark:bg-slate-900 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
                <h3 className="font-semibold text-slate-800 dark:text-slate-200">{definition.title}</h3>
            </div>

            <div className="flex-1 overflow-x-auto p-4">
                {columns.length === 0 ? (
                    <div className="h-full flex items-center justify-center border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg">
                        <p className="text-slate-500 dark:text-slate-400">No columns defined for this board.</p>
                    </div>
                ) : (
                    <div className="flex gap-4 h-full min-w-max">
                        {columns.map(column => (
                            <div key={column.id} className="w-72 flex flex-col bg-slate-100 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700">
                                {/* Column Header */}
                                <div className={`px-3 py-2 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center ${column.color || 'bg-slate-100 dark:bg-slate-800'}`}>
                                    <span className="font-medium text-sm text-slate-700 dark:text-slate-300">{column.title}</span>
                                    <div className="flex items-center gap-1">
                                        <span className="text-xs bg-white dark:bg-slate-700 px-1.5 py-0.5 rounded-full text-slate-500 dark:text-slate-400">
                                            {getColumnCards(column.id).length}
                                        </span>
                                        <button className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-500">
                                            <MoreHorizontal size={14} />
                                        </button>
                                    </div>
                                </div>

                                {/* Cards Container */}
                                <div className="flex-1 p-2 overflow-y-auto space-y-2">
                                    {getColumnCards(column.id).map(card => (
                                        <div
                                            key={card.id}
                                            onClick={() => handleCardClick(card)}
                                            className="p-3 bg-white dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 rounded-md cursor-pointer hover:shadow-md transition-shadow group"
                                        >
                                            <h4 className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-1 leading-tight group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                                {card.title}
                                            </h4>
                                            {card.description && (
                                                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-2">
                                                    {card.description}
                                                </p>
                                            )}
                                            {card.tags && card.tags.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {card.tags.map(tag => (
                                                        <span key={tag} className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 text-[10px] text-slate-600 dark:text-slate-300 rounded">
                                                            {tag}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>

                                {/* Column Footer (Add Button) */}
                                <div className="p-2 border-t border-slate-200 dark:border-slate-700">
                                    <button
                                        onClick={() => handleAddCard(column.id)}
                                        aria-label={`Add card to ${column.title}`}
                                        className="w-full py-1.5 flex items-center justify-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700/50 rounded transition-colors"
                                    >
                                        <Plus size={14} />
                                        <span>Add Card</span>
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
