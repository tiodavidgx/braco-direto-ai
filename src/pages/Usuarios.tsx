import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiClient } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { Checkbox } from "@/components/ui/checkbox";
import { Users, Plus, Trash2, UserCheck, UserX, Key, Loader2, Shield, User, FileEdit, ClipboardCheck, Phone, Car, Headset, Search as SearchIcon, Hammer } from "lucide-react";

interface UserData {
  id: number;
  email: string;
  nome: string;
  telefone?: string;
  ativo: boolean;
  role: "admin" | "operador" | "motorista";
  created_at: string;
  pode_pre_cadastro?: boolean;
  pode_revisao_cadastro?: boolean;
  crm_solicitante?: boolean;
  crm_analista?: boolean;
  acesso_montagem?: boolean;
}

// Função para aplicar máscara de telefone brasileiro
const formatTelefone = (value: string): string => {
  // Remove tudo que não é número
  const numbers = value.replace(/\D/g, '');
  
  // Limita a 11 dígitos
  const limited = numbers.slice(0, 11);
  
  // Aplica a máscara (XX) XXXXX-XXXX
  if (limited.length <= 2) {
    return limited;
  } else if (limited.length <= 7) {
    return `(${limited.slice(0, 2)}) ${limited.slice(2)}`;
  } else {
    return `(${limited.slice(0, 2)}) ${limited.slice(2, 7)}-${limited.slice(7)}`;
  }
};

// Remove a máscara para enviar ao backend
const unformatTelefone = (value: string): string => {
  return value.replace(/\D/g, '');
};

export default function Usuarios() {
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserData | null>(null);
  const [formData, setFormData] = useState({ 
    email: "", 
    nome: "", 
    telefone: "",
    password: "", 
    role: "operador" as "admin" | "operador" | "motorista",
    pode_pre_cadastro: false,
    pode_revisao_cadastro: false,
    crm_solicitante: false,
    crm_analista: false,
    acesso_montagem: false
  });
  const [newPassword, setNewPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    carregarUsuarios();
  }, []);

  const carregarUsuarios = async () => {
    try {
      const response = await apiClient.get<UserData[]>("/sistema/users");
      setUsers(response);
    } catch (error) {
      console.error("Erro ao carregar usuários:", error);
      toast.error("Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  };

  const criarUsuario = async () => {
    if (!formData.email || !formData.nome || !formData.password) {
      toast.error("Preencha todos os campos");
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.post("/sistema/users", formData);
      toast.success("Usuário criado com sucesso!");
      setDialogOpen(false);
      setFormData({ email: "", nome: "", telefone: "", password: "", role: "operador", pode_pre_cadastro: false, pode_revisao_cadastro: false, crm_solicitante: false, crm_analista: false, acesso_montagem: false });
      carregarUsuarios();
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar usuário");
    } finally {
      setSubmitting(false);
    }
  };

  const alterarStatus = async (user: UserData) => {
    try {
      await apiClient.put(`/sistema/users/${user.id}/status`, { ativo: !user.ativo });
      toast.success(`Usuário ${user.ativo ? "desativado" : "ativado"} com sucesso!`);
      carregarUsuarios();
    } catch (error: any) {
      toast.error(error.message || "Erro ao alterar status");
    }
  };

  const alterarRole = async (user: UserData, newRole: "admin" | "operador" | "motorista") => {
    if (user.id === currentUser?.id) {
      toast.error("Você não pode alterar seu próprio nível de acesso");
      return;
    }
    
    try {
      await apiClient.put(`/sistema/users/${user.id}/role`, { role: newRole });
      toast.success(`Nível de acesso alterado para ${newRole === "admin" ? "Administrador" : newRole === "motorista" ? "Motorista" : "Operador"}!`);
      carregarUsuarios();
    } catch (error: any) {
      toast.error(error.message || "Erro ao alterar nível de acesso");
    }
  };

  const alterarPermissoes = async (user: UserData, campo: "pode_pre_cadastro" | "pode_revisao_cadastro" | "crm_solicitante" | "crm_analista" | "acesso_montagem", valor: boolean) => {
    try {
      const novasPermissoes = {
        pode_pre_cadastro: user.pode_pre_cadastro ?? false,
        pode_revisao_cadastro: user.pode_revisao_cadastro ?? false,
        crm_solicitante: user.crm_solicitante ?? false,
        crm_analista: user.crm_analista ?? false,
        acesso_montagem: user.acesso_montagem ?? false,
        [campo]: valor
      };
      await apiClient.put(`/sistema/users/${user.id}/permissoes`, novasPermissoes);
      toast.success("Permissão atualizada com sucesso!");
      carregarUsuarios();
    } catch (error: any) {
      toast.error(error.message || "Erro ao alterar permissões");
    }
  };

  const alterarSenha = async () => {
    if (!selectedUser || !newPassword) {
      toast.error("Informe a nova senha");
      return;
    }

    if (newPassword.length < 6) {
      toast.error("Senha deve ter pelo menos 6 caracteres");
      return;
    }

    setSubmitting(true);
    try {
      await apiClient.put(`/sistema/users/${selectedUser.id}/password`, { password: newPassword });
      toast.success("Senha alterada com sucesso!");
      setPasswordDialogOpen(false);
      setNewPassword("");
      setSelectedUser(null);
    } catch (error: any) {
      toast.error(error.message || "Erro ao alterar senha");
    } finally {
      setSubmitting(false);
    }
  };

  const excluirUsuario = async (user: UserData) => {
    if (user.id === currentUser?.id) {
      toast.error("Você não pode excluir seu próprio usuário");
      return;
    }

    if (!confirm(`Deseja realmente excluir o usuário ${user.nome}?`)) {
      return;
    }

    try {
      await apiClient.delete(`/sistema/users/${user.id}`);
      toast.success("Usuário excluído com sucesso!");
      carregarUsuarios();
    } catch (error: any) {
      toast.error(error.message || "Erro ao excluir usuário");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Usuários</h1>
          <p className="text-muted-foreground">Gerencie os usuários do sistema</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Novo Usuário
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Criar Novo Usuário</DialogTitle>
              <DialogDescription>
                Preencha os dados para criar um novo usuário no sistema
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="nome">Nome</Label>
                <Input
                  id="nome"
                  placeholder="Nome do usuário"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="email@exemplo.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="telefone">Telefone (WhatsApp)</Label>
                <Input
                  id="telefone"
                  type="tel"
                  placeholder="(11) 99999-9999"
                  value={formatTelefone(formData.telefone)}
                  onChange={(e) => setFormData({ ...formData, telefone: unformatTelefone(e.target.value) })}
                />
                <p className="text-xs text-muted-foreground">
                  Usado para receber notificações via WhatsApp
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Nível de Acesso</Label>
                <Select 
                  value={formData.role} 
                  onValueChange={(value: "admin" | "operador" | "motorista") => setFormData({ ...formData, role: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o nível" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        Administrador - Acesso total
                      </div>
                    </SelectItem>
                    <SelectItem value="operador">
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4" />
                        Operador - Somente Custos Extras
                      </div>
                    </SelectItem>
                    <SelectItem value="motorista">
                      <div className="flex items-center gap-2">
                        <Car className="h-4 w-4" />
                        Motorista - Lançamento de Despesas
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Operadores só podem acessar Custos Extras. Motoristas só acessam a página de despesas.
                </p>
              </div>

              {/* Permissões de Pré-Cadastro */}
              <div className="space-y-3 pt-4 border-t">
                <Label>Permissões de Pré-Cadastro</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="pode_pre_cadastro"
                      checked={formData.pode_pre_cadastro}
                      onCheckedChange={(checked) => 
                        setFormData({ ...formData, pode_pre_cadastro: checked === true })
                      }
                    />
                    <label
                      htmlFor="pode_pre_cadastro"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                    >
                      <FileEdit className="h-4 w-4" />
                      Pode criar/editar Pré-Cadastro
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="pode_revisao_cadastro"
                      checked={formData.pode_revisao_cadastro}
                      onCheckedChange={(checked) => 
                        setFormData({ ...formData, pode_revisao_cadastro: checked === true })
                      }
                    />
                    <label
                      htmlFor="pode_revisao_cadastro"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                    >
                      <ClipboardCheck className="h-4 w-4" />
                      Pode revisar/aprovar cadastros
                    </label>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Defina quais áreas de pré-cadastro este usuário pode acessar
                </p>
              </div>

              {/* Permissões CRM */}
              <div className="space-y-3 pt-4 border-t">
                <Label>Permissões CRM</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="crm_solicitante"
                      checked={formData.crm_solicitante}
                      onCheckedChange={(checked) => 
                        setFormData({ ...formData, crm_solicitante: checked === true })
                      }
                    />
                    <label
                      htmlFor="crm_solicitante"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                    >
                      <Headset className="h-4 w-4" />
                      CRM Solicitante
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="crm_analista"
                      checked={formData.crm_analista}
                      onCheckedChange={(checked) => 
                        setFormData({ ...formData, crm_analista: checked === true })
                      }
                    />
                    <label
                      htmlFor="crm_analista"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                    >
                      <SearchIcon className="h-4 w-4" />
                      CRM Analista
                    </label>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Solicitante pode criar tickets. Analista recebe e trata tickets.
                </p>
              </div>

              {/* Permissões Montagem */}
              <div className="space-y-3 pt-4 border-t">
                <Label>Montagem 24h</Label>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="acesso_montagem"
                    checked={formData.acesso_montagem}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, acesso_montagem: checked === true })
                    }
                  />
                  <label
                    htmlFor="acesso_montagem"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex items-center gap-2"
                  >
                    <Hammer className="h-4 w-4" />
                    Acesso ao Kanban de Montagem 24h
                  </label>
                </div>
                <p className="text-xs text-muted-foreground">
                  Só usuários com esta permissão (ou administradores) verão o menu “Montagem 24h”.
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={criarUsuario} disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Criando...
                  </>
                ) : (
                  "Criar Usuário"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Lista de Usuários
          </CardTitle>
          <CardDescription>
            {users.length} usuário{users.length !== 1 ? "s" : ""} cadastrado{users.length !== 1 ? "s" : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Telefone</TableHead>
                  <TableHead>Nível de Acesso</TableHead>
                  <TableHead>Permissões Pré-Cadastro</TableHead>
                  <TableHead>Permissões CRM</TableHead>
                  <TableHead>Montagem</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.nome}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Phone className="h-3 w-3 text-muted-foreground" />
                        <Input
                          className="w-[140px] h-7 text-xs"
                          placeholder="(11) 99999-9999"
                          value={formatTelefone(user.telefone || "")}
                          onChange={(e) => {
                            const newUsers = users.map(u => 
                              u.id === user.id ? { ...u, telefone: unformatTelefone(e.target.value) } : u
                            );
                            setUsers(newUsers);
                          }}
                          onBlur={async (e) => {
                            try {
                              await apiClient.put(`/sistema/users/${user.id}/telefone`, { telefone: unformatTelefone(e.target.value) });
                              toast.success("Telefone salvo!");
                            } catch (error: any) {
                              toast.error("Erro ao salvar telefone");
                            }
                          }}
                        />
                      </div>
                    </TableCell>
                    <TableCell>
                      {user.id === currentUser?.id ? (
                        <Badge variant={user.role === "admin" ? "default" : "secondary"}
                          className={user.role === "motorista" ? "bg-blue-100 text-blue-800" : ""}
                        >
                          {user.role === "admin" ? (
                            <>
                              <Shield className="mr-1 h-3 w-3" />
                              Admin
                            </>
                          ) : user.role === "motorista" ? (
                            <>
                              <Car className="mr-1 h-3 w-3" />
                              Motorista
                            </>
                          ) : (
                            "Operador"
                          )}
                        </Badge>
                      ) : (
                        <Select
                          value={user.role}
                          onValueChange={(value: "admin" | "operador" | "motorista") => alterarRole(user, value)}
                        >
                          <SelectTrigger className="w-[140px] h-8">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">
                              <div className="flex items-center gap-1">
                                <Shield className="h-3 w-3" />
                                Admin
                              </div>
                            </SelectItem>
                            <SelectItem value="operador">Operador</SelectItem>
                            <SelectItem value="motorista">
                              <div className="flex items-center gap-1">
                                <Car className="h-3 w-3" />
                                Motorista
                              </div>
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id={`pre_cadastro_${user.id}`}
                            checked={user.pode_pre_cadastro ?? false}
                            onCheckedChange={(checked) => 
                              alterarPermissoes(user, "pode_pre_cadastro", checked === true)
                            }
                          />
                          <label
                            htmlFor={`pre_cadastro_${user.id}`}
                            className="text-xs flex items-center gap-1 cursor-pointer"
                          >
                            <FileEdit className="h-3 w-3" />
                            Criar/Editar
                          </label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id={`revisao_${user.id}`}
                            checked={user.pode_revisao_cadastro ?? false}
                            onCheckedChange={(checked) => 
                              alterarPermissoes(user, "pode_revisao_cadastro", checked === true)
                            }
                          />
                          <label
                            htmlFor={`revisao_${user.id}`}
                            className="text-xs flex items-center gap-1 cursor-pointer"
                          >
                            <ClipboardCheck className="h-3 w-3" />
                            Revisar
                          </label>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id={`crm_solicitante_${user.id}`}
                            checked={user.crm_solicitante ?? false}
                            onCheckedChange={(checked) => 
                              alterarPermissoes(user, "crm_solicitante", checked === true)
                            }
                          />
                          <label
                            htmlFor={`crm_solicitante_${user.id}`}
                            className="text-xs flex items-center gap-1 cursor-pointer"
                          >
                            <Headset className="h-3 w-3" />
                            Solicitante
                          </label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Checkbox
                            id={`crm_analista_${user.id}`}
                            checked={user.crm_analista ?? false}
                            onCheckedChange={(checked) => 
                              alterarPermissoes(user, "crm_analista", checked === true)
                            }
                          />
                          <label
                            htmlFor={`crm_analista_${user.id}`}
                            className="text-xs flex items-center gap-1 cursor-pointer"
                          >
                            <SearchIcon className="h-3 w-3" />
                            Analista
                          </label>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id={`acesso_montagem_${user.id}`}
                          checked={user.acesso_montagem ?? false}
                          onCheckedChange={(checked) =>
                            alterarPermissoes(user, "acesso_montagem", checked === true)
                          }
                        />
                        <label
                          htmlFor={`acesso_montagem_${user.id}`}
                          className="text-xs flex items-center gap-1 cursor-pointer"
                        >
                          <Hammer className="h-3 w-3" />
                          Montagem 24h
                        </label>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.ativo ? "default" : "secondary"}>
                        {user.ativo ? "Ativo" : "Inativo"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Alterar Senha"
                          onClick={() => {
                            setSelectedUser(user);
                            setPasswordDialogOpen(true);
                          }}
                        >
                          <Key className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title={user.ativo ? "Desativar" : "Ativar"}
                          onClick={() => alterarStatus(user)}
                        >
                          {user.ativo ? (
                            <UserX className="h-4 w-4 text-warning" />
                          ) : (
                            <UserCheck className="h-4 w-4 text-success" />
                          )}
                        </Button>
                        {user.id !== currentUser?.id && (
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Excluir"
                            onClick={() => excluirUsuario(user)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog de Alterar Senha */}
      <Dialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Alterar Senha</DialogTitle>
            <DialogDescription>
              Defina uma nova senha para {selectedUser?.nome}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="newPassword">Nova Senha</Label>
              <Input
                id="newPassword"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPasswordDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={alterarSenha} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                "Alterar Senha"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
