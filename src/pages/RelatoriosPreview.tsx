import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Download } from "lucide-react";

const RelatorioPrestadorPreview = () => {
  const dadosExemplo = {
    prestador_nome: "João Silva dos Santos",
    periodo: "Janeiro/2024",
    lote_id: "123456",
    data_geracao: "15/01/2024",
    os_list: [
      { num: 1, os_numero: "OS-2024-001", cliente: "Maria da Silva", servico: "Instalação de guarda-roupa", valor: 150.00 },
      { num: 2, os_numero: "OS-2024-002", cliente: "José Santos", servico: "Montagem de rack TV", valor: 80.00 },
      { num: 3, os_numero: "OS-2024-003", cliente: "Ana Paula Costa", servico: "Instalação de cozinha planejada", valor: 320.00 },
      { num: 4, os_numero: "OS-2024-004", cliente: "Carlos Eduardo Souza", servico: "Montagem de estante", valor: 120.00 },
      { num: 5, os_numero: "OS-2024-005", cliente: "Fernanda Lima", servico: "Instalação de closet", valor: 280.00 },
    ],
    quantidade_os: 5,
    valor_total: 950.00
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 bg-white p-8 shadow-lg">
      {/* Header */}
      <div className="border-t-4 border-primary pt-6">
        <h1 className="text-3xl font-bold text-primary text-center mb-2">RELATÓRIO DE FECHAMENTO</h1>
        <p className="text-center text-muted-foreground text-lg">Prestador de Serviços</p>
      </div>

      {/* Info Box */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3 w-1/4">Prestador:</td>
              <td className="p-3">{dadosExemplo.prestador_nome}</td>
            </tr>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Período:</td>
              <td className="p-3">{dadosExemplo.periodo}</td>
            </tr>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Lote ID:</td>
              <td className="p-3">{dadosExemplo.lote_id}</td>
            </tr>
            <tr>
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Data de Geração:</td>
              <td className="p-3">{dadosExemplo.data_geracao}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* OS Section */}
      <div className="space-y-3">
        <h2 className="text-xl font-bold text-[#1e40af]">Ordens de Serviço (OS)</h2>
        
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-primary text-white">
                <th className="p-2 text-center w-12">#</th>
                <th className="p-2 text-left w-28">OS</th>
                <th className="p-2 text-left">Cliente</th>
                <th className="p-2 text-left">Serviço</th>
                <th className="p-2 text-right w-24">Valor</th>
              </tr>
            </thead>
            <tbody>
              {dadosExemplo.os_list.map((os, idx) => (
                <tr key={os.num} className={idx % 2 === 0 ? "bg-white" : "bg-blue-50"}>
                  <td className="p-2 text-center border-t border-border">{os.num}</td>
                  <td className="p-2 border-t border-border">{os.os_numero}</td>
                  <td className="p-2 border-t border-border">{os.cliente}</td>
                  <td className="p-2 border-t border-border">{os.servico}</td>
                  <td className="p-2 text-right border-t border-border">R$ {os.valor.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Totals Box */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="bg-blue-50 border-b border-border">
              <td className="text-[#1e40af] font-bold p-3">Quantidade de OS:</td>
              <td className="text-right font-bold p-3">{dadosExemplo.quantidade_os}</td>
            </tr>
            <tr className="bg-green-500 text-white">
              <td className="font-bold p-4 text-lg">Valor Total:</td>
              <td className="text-right font-bold p-4 text-lg">R$ {dadosExemplo.valor_total.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Instructions */}
      <div className="space-y-3 pt-4">
        <p className="font-semibold text-foreground">📋 <strong>Próximos Passos:</strong></p>
        <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground ml-4">
          <li>Emita a Nota Fiscal referente aos serviços prestados no período</li>
          <li>Acesse o link de upload fornecido no email</li>
          <li>Anexe a Nota Fiscal em formato PDF</li>
          <li>Aguarde a confirmação de pagamento</li>
        </ol>
        <p className="text-xs text-muted-foreground text-center italic pt-4">
          Este documento é um comprovante dos serviços prestados no período especificado. 
          Mantenha-o guardado para sua contabilidade.
        </p>
      </div>

      {/* Footer */}
      <div className="border-t border-border pt-4 mt-8">
        <div className="flex justify-between items-center text-xs text-muted-foreground">
          <span>Gerado em: {dadosExemplo.data_geracao} às 14:30</span>
          <span className="font-bold text-primary">Novo Mundo - Sistema de Gestão</span>
          <span>Página 1</span>
        </div>
      </div>
    </div>
  );
};

const RelatorioMontadorPreview = () => {
  const dadosExemplo = {
    montador_nome: "Maria Santos Silva",
    periodo: "Janeiro/2024",
    envio_id: "789012",
    percentual_comissao: 15.0,
    data_geracao: "15/01/2024",
    montagens: [
      { num: 1, pedido: "PED-001", cliente: "Cliente XYZ Ltda", produto: "Guarda-roupa 6 portas", comissao: 120.00 },
      { num: 2, pedido: "PED-002", cliente: "João da Silva", produto: "Cozinha planejada", comissao: 280.00 },
      { num: 3, pedido: "PED-003", cliente: "Maria Costa", produto: "Rack para TV", comissao: 65.00 },
      { num: 4, pedido: "PED-004", cliente: "Pedro Santos", produto: "Estante modular", comissao: 95.00 },
      { num: 5, pedido: "PED-005", cliente: "Ana Paula", produto: "Closet planejado", comissao: 180.00 },
      { num: 6, pedido: "PED-006", cliente: "Carlos Eduardo", produto: "Painel TV com nicho", comissao: 75.00 },
    ],
    quantidade_montagens: 6,
    total_comissoes: 815.00,
    auxilio_semanal: 500.00,
    valor_final: 1315.00
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 bg-white p-8 shadow-lg">
      {/* Header */}
      <div className="border-t-4 border-primary pt-6">
        <h1 className="text-3xl font-bold text-primary text-center mb-2">RELATÓRIO DE PAGAMENTO</h1>
        <p className="text-center text-muted-foreground text-lg">Montador</p>
      </div>

      {/* Info Box */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3 w-1/4">Montador:</td>
              <td className="p-3">{dadosExemplo.montador_nome}</td>
            </tr>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Período:</td>
              <td className="p-3">{dadosExemplo.periodo}</td>
            </tr>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">ID do Envio:</td>
              <td className="p-3">{dadosExemplo.envio_id}</td>
            </tr>
            <tr className="border-b border-border">
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Comissão:</td>
              <td className="p-3">{dadosExemplo.percentual_comissao.toFixed(1)}%</td>
            </tr>
            <tr>
              <td className="bg-blue-50 text-[#1e40af] font-bold p-3">Data de Geração:</td>
              <td className="p-3">{dadosExemplo.data_geracao}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Montagens Section */}
      <div className="space-y-3">
        <h2 className="text-xl font-bold text-[#1e40af]">Montagens Realizadas</h2>
        
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-primary text-white">
                <th className="p-2 text-center w-12">#</th>
                <th className="p-2 text-left w-24">Pedido</th>
                <th className="p-2 text-left">Cliente</th>
                <th className="p-2 text-left">Produto</th>
                <th className="p-2 text-right w-28">Comissão</th>
              </tr>
            </thead>
            <tbody>
              {dadosExemplo.montagens.map((montagem, idx) => (
                <tr key={montagem.num} className={idx % 2 === 0 ? "bg-white" : "bg-blue-50"}>
                  <td className="p-2 text-center border-t border-border">{montagem.num}</td>
                  <td className="p-2 border-t border-border">{montagem.pedido}</td>
                  <td className="p-2 border-t border-border">{montagem.cliente}</td>
                  <td className="p-2 border-t border-border">{montagem.produto}</td>
                  <td className="p-2 text-right border-t border-border">R$ {montagem.comissao.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Calculations Box */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <tbody>
            <tr className="bg-blue-50 border-b border-border">
              <td className="text-[#1e40af] font-bold p-3">Quantidade de Montagens:</td>
              <td className="text-right font-bold p-3">{dadosExemplo.quantidade_montagens}</td>
            </tr>
            <tr className="bg-blue-50 border-b border-border">
              <td className="text-[#1e40af] font-bold p-3">Total em Comissões:</td>
              <td className="text-right font-bold p-3">R$ {dadosExemplo.total_comissoes.toFixed(2)}</td>
            </tr>
            <tr className="bg-blue-50 border-b border-border">
              <td className="text-[#1e40af] font-bold p-3">Auxílio Semanal:</td>
              <td className="text-right font-bold p-3">R$ {dadosExemplo.auxilio_semanal.toFixed(2)}</td>
            </tr>
            <tr className="bg-green-500 text-white">
              <td className="font-bold p-4 text-lg">Valor Final a Receber:</td>
              <td className="text-right font-bold p-4 text-lg">R$ {dadosExemplo.valor_final.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Instructions */}
      <div className="space-y-3 pt-4">
        <p className="font-semibold text-foreground">📋 <strong>Próximos Passos:</strong></p>
        <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground ml-4">
          <li>Emita a Nota Fiscal referente às montagens realizadas no período</li>
          <li>Acesse o link de upload fornecido no email</li>
          <li>Anexe a Nota Fiscal em formato PDF</li>
          <li>Aguarde a confirmação de pagamento</li>
        </ol>
        <p className="text-xs text-muted-foreground text-center italic pt-4">
          Este documento é um comprovante das montagens realizadas no período especificado. 
          As comissões são calculadas de acordo com o percentual definido em seu cadastro.
        </p>
      </div>

      {/* Footer */}
      <div className="border-t border-border pt-4 mt-8">
        <div className="flex justify-between items-center text-xs text-muted-foreground">
          <span>Gerado em: {dadosExemplo.data_geracao} às 14:30</span>
          <span className="font-bold text-primary">Novo Mundo - Sistema de Gestão</span>
          <span>Página 1</span>
        </div>
      </div>
    </div>
  );
};

export default function RelatoriosPreview() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Preview dos Relatórios</h1>
          <p className="text-muted-foreground mt-2">
            Visualize como ficam os relatórios em PDF (gerados com ReportLab)
          </p>
        </div>
        <Button variant="outline" className="gap-2">
          <Download className="w-4 h-4" />
          Documentação
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Modelos de Relatório
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="prestador" className="w-full">
            <TabsList className="grid w-full max-w-md grid-cols-2">
              <TabsTrigger value="prestador">Relatório de Prestador</TabsTrigger>
              <TabsTrigger value="montador">Relatório de Montador</TabsTrigger>
            </TabsList>
            
            <TabsContent value="prestador" className="mt-6">
              <div className="bg-gray-50 p-6 rounded-lg">
                <RelatorioPrestadorPreview />
              </div>
            </TabsContent>
            
            <TabsContent value="montador" className="mt-6">
              <div className="bg-gray-50 p-6 rounded-lg">
                <RelatorioMontadorPreview />
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>ℹ️ Informações Técnicas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <h3 className="font-semibold mb-2">🎨 Design dos PDFs</h3>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>Cores temáticas: Azul primário (#2563eb) e Verde (#10b981)</li>
              <li>Cabeçalho e rodapé em todas as páginas</li>
              <li>Tabelas com alternância de cores para melhor leitura</li>
              <li>Layout profissional com espaçamento adequado</li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-2">📄 Geração de PDFs</h3>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
              <li>Biblioteca: <code className="bg-muted px-1 py-0.5 rounded">ReportLab 4.0.7</code></li>
              <li>Localização: <code className="bg-muted px-1 py-0.5 rounded">backend_example/app/utils/pdf_generator.py</code></li>
              <li>Performance superior ao WeasyPrint</li>
              <li>Controle total sobre posicionamento e estilo</li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-2">🔗 Endpoints da API</h3>
            <div className="space-y-2 text-muted-foreground">
              <div className="flex items-center gap-2">
                <code className="bg-muted px-2 py-1 rounded text-xs">POST</code>
                <code className="bg-muted px-2 py-1 rounded text-xs">/api/v1/relatorios/prestador/:id/gerar</code>
              </div>
              <div className="flex items-center gap-2">
                <code className="bg-muted px-2 py-1 rounded text-xs">POST</code>
                <code className="bg-muted px-2 py-1 rounded text-xs">/api/v1/relatorios/montador/:id/gerar</code>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
