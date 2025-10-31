import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Home, MapPin, Package, Star, TrendingUp } from "lucide-react";

type MatchedShelter = {
  index: number;
  name: string;
  location: string;
  match_score: number;
  reason: string;
  full_data?: any;
};

type MatchResult = {
  success: boolean;
  matches: MatchedShelter[];
  reasoning: string;
  affected_area?: any;
  error?: string;
};

interface MatchedSheltersDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  matchResult: MatchResult | null;
  loading: boolean;
}

const MatchedSheltersDialog = ({ 
  open, 
  onOpenChange, 
  matchResult, 
  loading 
}: MatchedSheltersDialogProps) => {
  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600 dark:text-green-400";
    if (score >= 80) return "text-blue-600 dark:text-blue-400";
    if (score >= 70) return "text-yellow-600 dark:text-yellow-400";
    return "text-orange-600 dark:text-orange-400";
  };

  const getScoreBadgeVariant = (score: number): "default" | "secondary" | "destructive" | "outline" => {
    if (score >= 90) return "default";
    if (score >= 80) return "secondary";
    return "outline";
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <Star className="w-6 h-6 text-yellow-500" />
            AI-Matched Shelter Resources
          </DialogTitle>
          <DialogDescription>
            Top 3 shelters recommended by AI based on resources, capacity, and location
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center space-y-3">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              <p className="text-sm text-muted-foreground">Analyzing shelters and matching resources...</p>
            </div>
          </div>
        )}

        {!loading && matchResult && !matchResult.success && (
          <div className="p-6 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-destructive font-medium">Error: {matchResult.error || "Failed to match resources"}</p>
          </div>
        )}

        {!loading && matchResult && matchResult.success && (
          <div className="space-y-6">
            {/* Overall Reasoning */}
            {matchResult.reasoning && (
              <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
                <div className="flex items-start gap-3">
                  <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground mb-1">AI Analysis</p>
                    <p className="text-xs text-muted-foreground">{matchResult.reasoning}</p>
                  </div>
                </div>
              </Card>
            )}

            {/* Matched Shelters */}
            <div className="space-y-4">
              {matchResult.matches.map((match, idx) => (
                <Card key={idx} className="p-5 bg-card border-2 hover:border-primary/50 transition-colors">
                  <div className="space-y-3">
                    {/* Header with rank and score */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-bold text-lg">
                          #{idx + 1}
                        </div>
                        <div>
                          <h3 className="font-semibold text-lg text-foreground flex items-center gap-2">
                            {match.name}
                          </h3>
                          <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                            <MapPin className="w-3 h-3" />
                            {match.location}
                          </p>
                        </div>
                      </div>
                      <Badge 
                        variant={getScoreBadgeVariant(match.match_score)}
                        className="text-base px-3 py-1"
                      >
                        <span className={getScoreColor(match.match_score)}>
                          {match.match_score}% Match
                        </span>
                      </Badge>
                    </div>

                    {/* Reason */}
                    <div className="pl-13 space-y-2">
                      <p className="text-sm text-foreground bg-secondary/50 p-3 rounded-md">
                        <strong className="text-primary">Why this shelter?</strong> {match.reason}
                      </p>

                      {/* Shelter details if available */}
                      {match.full_data && (
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {match.full_data.capacity && (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Home className="w-3 h-3" />
                              <span>Capacity: {match.full_data.capacity}</span>
                            </div>
                          )}
                          {match.full_data.available_items && match.full_data.available_items.length > 0 && (
                            <div className="flex items-center gap-2 text-muted-foreground col-span-2">
                              <Package className="w-3 h-3" />
                              <div className="flex flex-wrap gap-1">
                                {match.full_data.available_items.slice(0, 5).map((item: string, i: number) => (
                                  <Badge key={i} variant="outline" className="text-xs">
                                    {item}
                                  </Badge>
                                ))}
                                {match.full_data.available_items.length > 5 && (
                                  <Badge variant="outline" className="text-xs">
                                    +{match.full_data.available_items.length - 5} more
                                  </Badge>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-2 pl-13">
                      <Button size="sm" className="flex-1">
                        Deploy Resources
                      </Button>
                      <Button size="sm" variant="outline">
                        View Details
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Footer */}
            <div className="flex justify-end pt-4 border-t">
              <Button onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default MatchedSheltersDialog;
