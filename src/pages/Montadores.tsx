import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
import { Search, Plus, Mail, Phone, Percent } from "lucide-react";

export default function Montadores() {
  const [searchTerm, setSearchTerm] = useState("");

  // Mock data
  const montadores = [
    {
      id: 1,
      nome: "João Silva",
      identificador: "MONT001",
      email: "joao.silva@email.com",
      telefone: "(11) 98765-1111",
      percentualComissao: 5.5,
      auxilioSemanal: 150.0,
      ativo: true,
    },
    {
      id: 2,
      nome: "Maria Santos",
      identificador: "MONT002",
      email: "maria.santos@email.com",
      telefone: "(11) 98765-2222",
      percentualComissao: 6.0,
      auxilioSemanal: 150.0,
      ativo: true,
    },
    {
      id: 3,
      nome: "Carlos Oliveira",
      identificador: "MONT003",
      email: "carlos.oliveira@email.com",
      telefone: "(11) 98765-3333",
      percentualComissao: 5.0,
      auxilioSemanal: 100.0,
      ativo: false,
    },
  ];

  const filteredMontadores = montadores.filter((m) =>
    m.nome.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Montadores</h1>
          <p className="text-muted-foreground">Gerenciar profissionais de montagem</p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Novo Montador
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar montadores..."
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
                <TableHead>Identificador</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>Comissão</TableHead>
                <TableHead>Auxílio Semanal</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMontadores.map((montador) => (
                <TableRow key={montador.id}>
                  <TableCell className="font-medium">{montador.nome}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{montador.identificador}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-sm">
                        <Mail className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{montador.email}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm">
                        <Phone className="h-3 w-3 text-muted-foreground" />
                        <span className="text-muted-foreground">{montador.telefone}</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Percent className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">{montador.percentualComissao}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="font-medium">
                      R$ {montador.auxilioSemanal.toFixed(2)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={montador.ativo ? "default" : "secondary"}
                      className={
                        montador.ativo ? "bg-success text-success-foreground" : ""
                      }
                    >
                      {montador.ativo ? "Ativo" : "Inativo"}
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
