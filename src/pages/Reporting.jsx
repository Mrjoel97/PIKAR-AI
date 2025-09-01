import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileDown, Database, Type, BarChart2 } from 'lucide-react';

export default function Reporting() {
    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <h1 className="text-3xl font-bold">Advanced Reporting Engine</h1>
            <div className="grid grid-cols-12 gap-6 h-[70vh]">
                <div className="col-span-3 space-y-4">
                    <Card>
                        <CardHeader><CardTitle>Data Sources</CardTitle></CardHeader>
                        <CardContent>
                            <ul><li><Database className="w-4 h-4 mr-2 inline" />Initiatives</li></ul>
                        </CardContent>
                    </Card>
                    <Card>
                        <CardHeader><CardTitle>Fields</CardTitle></CardHeader>
                        <CardContent>
                            <ul><li><Type className="w-4 h-4 mr-2 inline" />Name</li></ul>
                        </CardContent>
                    </Card>
                </div>
                <div className="col-span-9">
                    <Card className="h-full">
                        <CardHeader className="flex flex-row justify-between items-center">
                            <div>
                                <CardTitle>Report Builder</CardTitle>
                                <CardDescription>Drag and drop fields to build your report.</CardDescription>
                            </div>
                            <div>
                                <Button><FileDown className="w-4 h-4 mr-2" /> Export</Button>
                            </div>
                        </CardHeader>
                        <CardContent className="flex items-center justify-center h-5/6 border-2 border-dashed m-6 rounded-lg">
                            <div className="text-center text-gray-500">
                                <BarChart2 className="w-16 h-16 mx-auto mb-2" />
                                <p>Report Canvas</p>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}