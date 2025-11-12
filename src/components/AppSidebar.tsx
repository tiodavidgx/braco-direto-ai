import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
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
import { cn } from "@/lib/utils";

const menuItems = [
  {
    title: "Principal",
    items: [
      { title: "Dashboard", url: "/", icon: LayoutDashboard },
      { title: "Prestadores", url: "/prestadores", icon: Users },
      { title: "Montadores", url: "/montadores", icon: Wrench },
    ],
  },
  {
    title: "Relatórios",
    items: [
      { title: "Envio de Relatórios", url: "/envio-relatorios", icon: FileText },
      { title: "Histórico de Envios", url: "/historico-envios", icon: Clock },
    ],
  },
  {
    title: "Financeiro",
    items: [
      { title: "Pagamentos Vencidos", url: "/pagamentos-vencidos", icon: DollarSign },
      { title: "Upload de NFs", url: "/upload-nf", icon: Upload },
    ],
  },
  {
    title: "Comunicação",
    items: [
      { title: "WhatsApp", url: "/whatsapp", icon: MessageSquare },
      { title: "Automação", url: "/automacao", icon: Zap },
    ],
  },
  {
    title: "Sistema",
    items: [
      { title: "Configurar Email", url: "/email-config", icon: Settings },
      { title: "Jobs Automáticos", url: "/jobs", icon: Clock },
      { title: "Integrações", url: "/integracoes", icon: Settings },
      { title: "Backups", url: "/backups", icon: Database },
    ],
  },
];

export function AppSidebar() {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <Sidebar className="border-r border-border">
      <SidebarHeader className="border-b border-border px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
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
        {menuItems.map((group) => (
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
            <span className="text-sm font-medium">AD</span>
          </div>
          <div className="flex flex-col overflow-hidden">
            <span className="truncate text-sm font-medium">Admin</span>
            <span className="truncate text-xs text-muted-foreground">admin@novomundo.com</span>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
