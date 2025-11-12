import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { jobsService } from '@/services/jobs.service';
import { Play } from 'lucide-react';

export default function JobsSimple() {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<any>(null);

  const executarJob = async () => {
    setLoading(true);
    try {
      await jobsService.executarConsultaNotas();
      toast({ title: 'Sucesso', description: 'Job iniciado!' });
      
      // Aguardar e buscar resultado
      setTimeout(async () => {
        const data = await jobsService.getResultadoConsultaNotas();
        setResultado(data);
      }, 2000);
    } catch (error: any) {
      console.error('Erro:', error);
      toast({ 
        title: 'Erro', 
        description: error?.message || 'Erro ao executar job',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Jobs</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Teste de Job</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={executarJob} disabled={loading}>
            <Play className="h-4 w-4 mr-2" />
            Executar Job de Consulta de Notas
          </Button>
          
          {resultado && (
            <div className="mt-4">
              <pre className="bg-muted p-4 rounded">
                {JSON.stringify(resultado, null, 2)}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
