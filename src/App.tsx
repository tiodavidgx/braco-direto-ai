import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { NotificationContainer } from "@/components/NotificationContainer";
import { AuthProvider } from "@/contexts/AuthContext";
import PrivateRoute from "@/components/PrivateRoute";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import Prestadores from "./pages/Prestadores";
import Montadores from "./pages/Montadores";
import EnvioRelatorios from "./pages/EnvioRelatorios";
import EnvioRelatoriosMontadores from "./pages/EnvioRelatoriosMontadores";
import HistoricoEnvios from "./pages/HistoricoEnvios";
import PagamentosVencidos from "./pages/PagamentosVencidos";
import WhatsApp from "./pages/WhatsApp";
import Automacao from "./pages/Automacao";
import Integracoes from "./pages/Integracoes";
import Jobs from "./pages/Jobs";
import EmailConfig from "./pages/EmailConfig";
import RelatoriosPreview from "./pages/RelatoriosPreview";
import UploadNF from "./pages/UploadNF";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

// Layout com sidebar para páginas internas
const MainLayout = ({ children }: { children: React.ReactNode }) => (
  <SidebarProvider>
    <div className="flex min-h-screen w-full bg-background">
      <AppSidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="container mx-auto p-8">
          {children}
        </div>
      </main>
    </div>
  </SidebarProvider>
);

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <NotificationContainer />
          <Routes>
            {/* Rota de login - pública */}
            <Route path="/login" element={<LoginPage />} />
            
            {/* Rota pública de upload - sem sidebar */}
            <Route path="/upload/nf/:hash" element={<UploadNF />} />
            
            {/* Rotas do sistema - protegidas com sidebar */}
            <Route path="/" element={<PrivateRoute><MainLayout><Dashboard /></MainLayout></PrivateRoute>} />
            <Route path="/prestadores" element={<PrivateRoute><MainLayout><Prestadores /></MainLayout></PrivateRoute>} />
            <Route path="/montadores" element={<PrivateRoute><MainLayout><Montadores /></MainLayout></PrivateRoute>} />
            <Route path="/envio-relatorios" element={<PrivateRoute><MainLayout><EnvioRelatorios /></MainLayout></PrivateRoute>} />
            <Route path="/envio-montadores" element={<PrivateRoute><MainLayout><EnvioRelatoriosMontadores /></MainLayout></PrivateRoute>} />
            <Route path="/historico-envios" element={<PrivateRoute><MainLayout><HistoricoEnvios /></MainLayout></PrivateRoute>} />
            <Route path="/pagamentos-vencidos" element={<PrivateRoute><MainLayout><PagamentosVencidos /></MainLayout></PrivateRoute>} />
            <Route path="/whatsapp" element={<PrivateRoute><MainLayout><WhatsApp /></MainLayout></PrivateRoute>} />
            <Route path="/automacao" element={<PrivateRoute><MainLayout><Automacao /></MainLayout></PrivateRoute>} />
            <Route path="/integracoes" element={<PrivateRoute><MainLayout><Integracoes /></MainLayout></PrivateRoute>} />
            <Route path="/jobs" element={<PrivateRoute><MainLayout><Jobs /></MainLayout></PrivateRoute>} />
            <Route path="/email-config" element={<PrivateRoute><MainLayout><EmailConfig /></MainLayout></PrivateRoute>} />
            <Route path="/auth/callback" element={<PrivateRoute><MainLayout><EmailConfig /></MainLayout></PrivateRoute>} />
            <Route path="/relatorios-preview" element={<PrivateRoute><MainLayout><RelatoriosPreview /></MainLayout></PrivateRoute>} />
            
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
