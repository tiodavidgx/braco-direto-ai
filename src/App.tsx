import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { NotificationContainer } from "@/components/NotificationContainer";
import { AuthProvider } from "@/contexts/AuthContext";
import { PrivateRoute } from "@/components/PrivateRoute";
import { Menu } from "lucide-react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Prestadores from "./pages/Prestadores";
import Montadores from "./pages/Montadores";
import PreCadastroMontadores from "./pages/PreCadastroMontadores";
import RevisaoCadastroMontador from "./pages/RevisaoCadastroMontador";
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
import Usuarios from "./pages/Usuarios";
import CustosExtras from "./pages/CustosExtras";
import MMS from "./pages/MMS";
import GestaoPagamentos from "./pages/GestaoPagamentos";
import CalendarioPagamentos from "./pages/CalendarioPagamentos";
import LancamentosMotorista from "./pages/LancamentosMotorista";
import DespesasMotoristas from "./pages/DespesasMotoristas";
import Terceirizadas from "./pages/Terceirizadas";
import PagamentosTerceirizada from "./pages/PagamentosTerceirizada";
import EnvioAutomaticoMontadores from "./pages/EnvioAutomaticoMontadores";
import Aprovacoes from "./pages/Aprovacoes";
import EmailTemplates from "./pages/EmailTemplates";
import CRM from "./pages/CRM";
import CRMParametros from "./pages/CRMParametros";
import AcompanhamentoMontagem from "./pages/AcompanhamentoMontagem";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

// Layout com sidebar (para rotas autenticadas)
function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <AppSidebar />
        <main className="flex-1 overflow-y-auto">
          {/* Header mobile com botão de menu */}
          <header className="sticky top-0 z-40 flex h-14 items-center gap-4 border-b bg-background px-4 md:hidden">
            <SidebarTrigger className="h-9 w-9">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Abrir menu</span>
            </SidebarTrigger>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                <span className="text-sm font-bold text-primary-foreground">BD</span>
              </div>
              <span className="font-semibold">Braço Direito</span>
            </div>
          </header>
          <div className="container mx-auto p-4 md:p-8">
            {children}
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <AuthProvider>
        <Toaster />
        <Sonner />
        <NotificationContainer />
        <BrowserRouter>
          <Routes>
            {/* Rotas públicas */}
            <Route path="/login" element={<Login />} />
            <Route path="/motorista" element={<LancamentosMotorista />} />
            
            {/* Rotas apenas para Admin */}
            <Route path="/" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Dashboard /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/prestadores" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Prestadores /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/montadores" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Montadores /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/pre-cadastro-montadores" element={
              <PrivateRoute requiredPermission="pode_pre_cadastro">
                <AuthenticatedLayout><PreCadastroMontadores /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/revisao-cadastro-montador" element={
              <PrivateRoute requiredPermission="pode_revisao_cadastro">
                <AuthenticatedLayout><RevisaoCadastroMontador /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/envio-relatorios" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EnvioRelatorios /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/envio-montadores" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EnvioRelatoriosMontadores /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/historico-envios" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><HistoricoEnvios /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/pagamentos-vencidos" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><PagamentosVencidos /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/whatsapp" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><WhatsApp /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/automacao" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Automacao /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/integracoes" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Integracoes /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/jobs" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Jobs /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/email-config" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EmailConfig /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/auth/callback" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EmailConfig /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/relatorios-preview" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><RelatoriosPreview /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/usuarios" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Usuarios /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* CRM - Acessível por usuários com permissão CRM */}
            <Route path="/crm" element={
              <PrivateRoute requiredPermission="crm_access">
                <AuthenticatedLayout><CRM /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/crm/parametros" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><CRMParametros /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* Rota acessível por todos (Admin e Operador) */}
            <Route path="/custos-extras" element={
              <PrivateRoute>
                <AuthenticatedLayout><CustosExtras /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* MMS - Limpeza de Dados - Liberado para todos os usuários */}
            <Route path="/mms" element={
              <PrivateRoute>
                <AuthenticatedLayout><MMS /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* Gestão de Pagamentos - Apenas Admin */}
            <Route path="/gestao-pagamentos" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><GestaoPagamentos /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* Calendário de Pagamentos - Admin e Operadores */}
            <Route path="/calendario-pagamentos" element={
              <PrivateRoute>
                <AuthenticatedLayout><CalendarioPagamentos /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            {/* Despesas dos Motoristas - Apenas Admin */}
            <Route path="/despesas-motoristas" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><DespesasMotoristas /></AuthenticatedLayout>
              </PrivateRoute>
            } />

            {/* Acompanhamento de Montagem */}
            <Route path="/acompanhamento-montagem" element={
              <PrivateRoute requiredPermission="acesso_montagem">
                <AuthenticatedLayout><AcompanhamentoMontagem /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            
            
            {/* Envio Automático - Montadores */}
            <Route path="/envio-automatico-montadores" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EnvioAutomaticoMontadores /></AuthenticatedLayout>
              </PrivateRoute>
            } />

            {/* Terceirizadas */}
            <Route path="/terceirizadas" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Terceirizadas /></AuthenticatedLayout>
              </PrivateRoute>
            } />
            <Route path="/terceirizadas/:id/pagamentos" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><PagamentosTerceirizada /></AuthenticatedLayout>
              </PrivateRoute>
            } />

            {/* Aprovações */}
            <Route path="/aprovacoes" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><Aprovacoes /></AuthenticatedLayout>
              </PrivateRoute>
            } />

            {/* Templates de Email */}
            <Route path="/email-templates" element={
              <PrivateRoute adminOnly>
                <AuthenticatedLayout><EmailTemplates /></AuthenticatedLayout>
              </PrivateRoute>
            } />

            {/* Rota 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
