import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Search, Plus, Mail, Phone, Calendar } from "lucide-react";

export default function Prestadores() {
  const [searchTerm, setSearchTerm] = useState("");

  // Mock data - será substituído por dados reais da API
  const prestadores = [
    {
      id: 1,
      nome: "Prestadora ABC Ltda",
      email: "contato@abc.com",
      fornecedorId: "FOR123",
      telefone: "(11) 98765-4321",
      regraEnvio: "Semanal",
      diasEnvio: "Segunda-feira",
      tempoVencimento: 10,
      status: "ativo",
    },
    {
      id: 2,
      nome: "Serviços XYZ",
      email: "admin@xyz.com.br",
      fornecedorId: "FOR456",
      telefone: "(11) 91234-5678",
      regraEnvio: "Quinzenal",
      diasEnvio: "1, 15",
      tempoVencimento: 15,
      status: "ativo",
    },
    {
      id: 3,
      nome: "Prestadora 123",
      email: "contato@123.com",
      fornecedorId: "FOR789",
      telefone: "(11) 99999-8888",
      regraEnvio: "Mensal (Dia Fixo)",
      diasEnvio: "5",
      tempoVencimento: 10,
      status: "pendente",
    },
  ];

  const filteredPrestadores = prestadores.filter((p) =>
    p.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Prestadores</h1>
          <p className="text-muted-foreground">Gerenciar empresas prestadoras de serviços</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Novo Prestador
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar prestadores..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>Fornecedor ID</TableHead>
                <TableHead>Regra de Envio</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPrestadores.map((prestador) => (
                <TableRow key={prestador.id}>
                  <TableCell className="font-medium">{prestador.nome}</TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{prestador.email}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{prestador.telefone}</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{prestador.fornecedorId}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Calendar className="h-3 w-3 text-muted-foreground" />
                        <span className="font-medium">{prestador.regraEnvio}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{prestador.diasEnvio}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={prestador.status === "ativo" ? "default" : "secondary"}
                      className={
                        prestador.status === "ativo"
                          ? "bg-success text-success-foreground"
                          : ""
                      }
                    >
                      {prestador.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm">
                      Editar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
