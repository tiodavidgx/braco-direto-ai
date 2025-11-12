import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import Dashboard from "./pages/Dashboard";
import Prestadores from "./pages/Prestadores";
import Montadores from "./pages/Montadores";
import EnvioRelatorios from "./pages/EnvioRelatorios";
import HistoricoEnvios from "./pages/HistoricoEnvios";
import PagamentosVencidos from "./pages/PagamentosVencidos";
import WhatsApp from "./pages/WhatsApp";
import Automacao from "./pages/Automacao";
import Integracoes from "./pages/Integracoes";
import Jobs from "./pages/Jobs";
import EmailConfig from "./pages/EmailConfig";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <SidebarProvider>
          <div className="flex min-h-screen w-full bg-background">
            <AppSidebar />
            <main className="flex-1 overflow-y-auto">
              <div className="container mx-auto p-8">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/prestadores" element={<Prestadores />} />
                  <Route path="/montadores" element={<Montadores />} />
                  <Route path="/envio-relatorios" element={<EnvioRelatorios />} />
                  <Route path="/historico-envios" element={<HistoricoEnvios />} />
                  <Route path="/pagamentos-vencidos" element={<PagamentosVencidos />} />
                  <Route path="/whatsapp" element={<WhatsApp />} />
                  <Route path="/automacao" element={<Automacao />} />
                  <Route path="/integracoes" element={<Integracoes />} />
                  <Route path="/jobs" element={<Jobs />} />
                  <Route path="/email-config" element={<EmailConfig />} />
                  <Route path="/auth/callback" element={<EmailConfig />} />
                  {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </div>
            </main>
          </div>
        </SidebarProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
