import { useState, useRef, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm the DisasterAI Response Coordinator. I can help you with situation analysis, resource coordination, and real-time intelligence. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Try a few possible backend endpoints in order. Many dev setups run the
      // local FastAPI server in `mcp-hub` on port 8000 (see mcp-hub/api_server.py).
      // First try the app-relative endpoint (useful when a proxy maps /api/*),
      // then try the local FastAPI assistant/converse endpoint, then the chat
      // endpoint. This keeps the UI working in multiple environments.
      const prompt = input;

      // helper to try an endpoint and return parsed JSON or throw
      const tryFetch = async (url: string, body: any) => {
        const r = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error(`Network error: ${r.status} for ${url}`);
        return r.json().catch(() => ({} as any));
      };

      // 1) try app-relative (proxy/deployment)
      let json: any = {};
      try {
        json = await tryFetch("/api/disaster-chat", { message: prompt });
      } catch (e1) {
        // 2) try local mcp-hub assistant converse (returns { ok, session_id, reply })
        try {
          json = await tryFetch("http://127.0.0.1:8000/assistant/converse", { message: prompt });
        } catch (e2) {
          // 3) try local mcp-hub chat endpoint (returns { ok, response })
          try {
            json = await tryFetch("http://127.0.0.1:8000/chat", { messages: [{ role: "user", content: prompt }] });
          } catch (e3) {
            // rethrow the last error so outer catch handles fallback
            throw e3;
          }
        }
      }

      // Normalize backend response into a text reply
      const reply = (json && (json.response || json.reply)) || `(offline) I heard: ${prompt}`;
      const assistantMessage: Message = { role: "assistant", content: reply };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error:", error);
      toast({
        title: "Error",
        description: "Failed to get response. Showing a local fallback.",
        variant: "destructive",
      });

      // Local fallback so the chat remains usable without Supabase.
      const fallback: Message = {
        role: "assistant",
        content: "I'm unable to reach the remote service right now. Try again later or configure a backend at /api/disaster-chat.",
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-[600px] bg-card border-border">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-primary" />
          <h3 className="font-semibold text-foreground">AI Assistant</h3>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-secondary text-secondary-foreground rounded-lg p-3">
              <p className="text-sm">Analyzing...</p>
            </div>
          </div>
        )}
      </div>

      

      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                // Prevent form submission / newline insertion behavior
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask about situation, resources, or get recommendations..."
            disabled={isLoading}
            className="flex-1 bg-input border-border"
          />
          <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
};

export default ChatInterface;
