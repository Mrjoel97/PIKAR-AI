import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lightbulb, TrendingUp, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { createPageUrl } from '@/utils';

const suggestions = [
  {
    title: "Launch a New Product",
    description: "Use the full 6-phase journey to take a product from concept to market sustainability.",
    icon: Lightbulb,
  },
  {
    title: "Optimize Sales Funnel",
    description: "Analyze your sales process and use AI to identify bottlenecks and increase conversion.",
    icon: TrendingUp,
  },
  {
    title: "Improve Operational Efficiency",
    description: "Map a core business process and use the Operations Agent to streamline it.",
    icon: Zap,
  }
];

export default function SuggestedInitiatives() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Start a New Transformation</CardTitle>
        <CardDescription>Not sure where to begin? Here are some ideas to leverage the PIKAR AI platform.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {suggestions.map((suggestion, index) => (
          <div key={index} className="p-3 border rounded-lg flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/50">
            <div className="flex items-center gap-4">
              <suggestion.icon className="w-6 h-6 text-blue-500" />
              <div>
                <h4 className="font-semibold">{suggestion.title}</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">{suggestion.description}</p>
              </div>
            </div>
            <Link to={createPageUrl("CreateInitiative")}>
              <Button variant="ghost" size="sm">Start</Button>
            </Link>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}