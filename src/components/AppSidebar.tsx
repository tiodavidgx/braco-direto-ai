import { useState, useEffect } from "react";
import { useLocation, Link, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Wrench,
  DollarSign,
  FileText,
  Upload,
  MessageSquare,
  Zap,
  Clock,
  Settings,
  Database,
  Menu,
  ChevronLeft,
  Eye,
  LogOut,
  Shield,
  FileSpreadsheet,
  UserPlus,
  ClipboardCheck,
  CalendarDays,
  Car,
  Headset,
  Hammer,
  Building2,
  Mail,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";

interface MenuItem {
  title: string;
  url: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  requiredPermission?: "pode_pre_cadastro" | "pode_revisao_cadastro" | "crm_access" | "acesso_montagem";
}

interface MenuGroup {
  title: string;
  adminOnly?: boolean;
  items: MenuItem[];
}

// Menu items com controle de acesso
// adminOnly: true = só admin pode ver
// requiredPermission: permissão específica necessária
const menuItemsConfig: MenuGroup[] = [
  {
    title: "Principal",
    adminOnly: true,
    items: [
      { title: "Dashboard", url: "/", icon: LayoutDashboard },
      { title: "Prestadores", url: "/prestadores", icon: Users },
      { title: "Montadores", url: "/montadores", icon: Wrench },
    ],
  },
  {
    title: "Cadastros",
    adminOnly: false,
    items: [
      { title: "Pré-Cadastro Montadores", url: "/pre-cadastro-montadores", icon: UserPlus, adminOnly: false, requiredPermission: "pode_pre_cadastro" },
      { title: "Revisão de Cadastros", url: "/revisao-cadastro-montador", icon: ClipboardCheck, adminOnly: false, requiredPermission: "pode_revisao_cadastro" },
    ],
  },
  {
    title: "Operacao montagem",
    adminOnly: false,
    items: [
      { title: "Montagem 24h", url: "/acompanhamento-montagem", icon: Hammer, adminOnly: false, requiredPermission: "acesso_montagem" },
    ],
  },
  {
    title: "Relatórios",
    adminOnly: true,
    items: [
      { title: "Envio de Relatórios", url: "/envio-relatorios", icon: FileText },
      { title: "Envio de Montadores", url: "/envio-montadores", icon: Wrench },
      { title: "Envio Automático", url: "/envio-automatico-montadores", icon: Zap },
      { title: "Histórico de Envios", url: "/historico-envios", icon: Clock },
      { title: "Preview de Relatórios", url: "/relatorios-preview", icon: Eye },
    ],
  },
  {
    title: "Financeiro",
    adminOnly: false,
    items: [
      { title: "Gestão de Pagamentos", url: "/gestao-pagamentos", icon: CalendarDays, adminOnly: true },
      { title: "Calendário de Pagamentos", url: "/calendario-pagamentos", icon: CalendarDays, adminOnly: false },
      { title: "Pagamentos Vencidos", url: "/pagamentos-vencidos", icon: DollarSign, adminOnly: true },
      { title: "Custos Extras", url: "/custos-extras", icon: DollarSign, adminOnly: false },
      { title: "Despesas Motoristas", url: "/despesas-motoristas", icon: Car, adminOnly: true },
      { title: "Upload de NFs", url: "/upload-nf", icon: Upload, adminOnly: true },
      { title: "Terceirizadas", url: "/terceirizadas", icon: Building2, adminOnly: true },
    ],
  },
  {
    title: "CRM",
    adminOnly: false,
    items: [
      { title: "Painel CRM", url: "/crm", icon: Headset, adminOnly: false, requiredPermission: "crm_access" },
      { title: "Parâmetros", url: "/crm/parametros", icon: Settings, adminOnly: true },
    ],
  },
  {
    title: "Comunicação",
    adminOnly: true,
    items: [
      { title: "WhatsApp", url: "/whatsapp", icon: MessageSquare },
      { title: "Automação", url: "/automacao", icon: Zap },
      { title: "Templates de Email", url: "/email-templates", icon: Mail },
    ],
  },
  {
    title: "Sistema",
    adminOnly: true,
    items: [
      { title: "Usuários", url: "/usuarios", icon: Users },
      { title: "Configurar Email", url: "/email-config", icon: Settings },
      { title: "Jobs Automáticos", url: "/jobs", icon: Clock },
      { title: "Aprovações", url: "/aprovacoes", icon: Shield },
      { title: "Integrações", url: "/integracoes", icon: Settings },
      { title: "Backups", url: "/backups", icon: Database },
    ],
  },
  {
    title: "MMS",
    adminOnly: false,
    items: [
      { title: "Limpeza de Dados", url: "/mms", icon: FileSpreadsheet },
    ],
  },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentPath = location.pathname;
  const [version, setVersion] = useState("...");
  const { user, logout, isAdmin } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  useEffect(() => {
    // Carregar versão do sistema
    fetch('/version.json')
      .then(res => res.json())
      .then(data => setVersion(data.version))
      .catch(() => setVersion("1.0.0"));
  }, []);

  // Filtrar menu baseado no role do usuário e permissões
  const filteredMenuItems = menuItemsConfig
    .filter(group => isAdmin || !group.adminOnly)
    .map(group => ({
      ...group,
      items: group.items.filter(item => {
        // Admin tem acesso a tudo
        if (isAdmin) return true;
        
        // Se item é adminOnly, não mostra para não-admin
        if (item.adminOnly) return false;
        
        // Verificar permissão específica
        if (item.requiredPermission) {
          if (item.requiredPermission === 'crm_access') {
            return user?.crm_solicitante === true || user?.crm_analista === true;
          }
          if (item.requiredPermission === 'acesso_montagem') {
            return user?.acesso_montagem === true;
          }
          return user?.[item.requiredPermission] === true;
        }
        
        return true;
      })
    }))
    .filter(group => group.items.length > 0);

  return (
    <Sidebar className="border-r border-border">
      <SidebarHeader className="border-b border-border px-6 py-4">
        <Link to={isAdmin ? "/" : "/custos-extras"} className="flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
            <span className="text-lg font-bold text-primary-foreground">BD</span>
          </div>
          <div className="flex flex-col">
            <span className="text-lg font-semibold text-foreground">Braço Direito</span>
            <span className="text-xs text-muted-foreground">Sistema de Gestão</span>
          </div>
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {filteredMenuItems.map((group) => (
          <SidebarGroup key={group.title}>
            <SidebarGroupLabel className="px-4 text-xs font-medium text-muted-foreground">
              {group.title}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const isActive = currentPath === item.url;
                  return (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild isActive={isActive}>
                        <Link
                          to={item.url}
                          className={cn(
                            "flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors",
                            isActive
                              ? "bg-primary text-primary-foreground"
                              : "text-muted-foreground hover:bg-muted hover:text-foreground"
                          )}
                        >
                          <item.icon className="h-5 w-5" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter className="border-t border-border p-4">
        <div className="flex items-center gap-3 rounded-lg bg-muted p-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <span className="text-sm font-medium">{user?.nome?.substring(0, 2).toUpperCase() || "US"}</span>
          </div>
          <div className="flex flex-1 flex-col overflow-hidden">
            <span className="truncate text-sm font-medium">{user?.nome || "Usuário"}</span>
            <div className="flex items-center gap-1">
              <span className="truncate text-xs text-muted-foreground">{user?.email || ""}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge variant={isAdmin ? "default" : "secondary"} className="text-xs">
              {isAdmin ? (
                <>
                  <Shield className="mr-1 h-3 w-3" />
                  Admin
                </>
              ) : (
                "Operador"
              )}
            </Badge>
            <div className="flex items-center gap-1">
              <span className="text-xs font-mono text-muted-foreground">v{version}</span>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                onClick={handleLogout}
                title="Sair"
              >
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
