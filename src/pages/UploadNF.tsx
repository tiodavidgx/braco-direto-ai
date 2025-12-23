import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  FileText, Upload, CheckCircle, XCircle, Clock, 
  File, Trash2, AlertTriangle, Loader2 
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3080';

interface UploadInfo {
  hash: string;
  tipo: 'prestador' | 'montador';
  nome: string;
  email?: string;
  lote_id?: number;
  envio_id?: number;
  periodo: string;
  valor_total: number;
  quantidade_os: number;
  status: number;
  status_descricao: string;
  data_expiracao: string;
  dias_restantes: number;
  link_valido: boolean;
  arquivos_enviados: Array<{
    nome: string;
    extensao: string;
    tamanho: number;
    tamanho_formatado: string;
    data: string;
  }>;
}

interface FileWithPreview extends File {
  preview?: string;
}

export default function UploadNF() {
  const { hash } = useParams<{ hash: string }>();
  const [info, setInfo] = useState<UploadInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const fetchInfo = useCallback(async () => {
    if (!hash) return;
    
    try {
      const response = await fetch(`${API_URL}/api/v1/upload-nf/info/${hash}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Link não encontrado ou inválido');
        }
        throw new Error('Erro ao carregar informações');
      }
      
      const data = await response.json();
      setInfo(data);
      
      if (data.status === 1) {
        setUploadSuccess(true);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [hash]);

  useEffect(() => {
    fetchInfo();
  }, [fetchInfo]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  };

  const handleFiles = (newFiles: File[]) => {
    const validExtensions = ['.pdf', '.xml', '.jpg', '.jpeg', '.png'];
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    const validFiles = newFiles.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase();
      if (!validExtensions.includes(ext)) {
        alert(`Arquivo ${file.name}: Extensão não permitida. Use PDF, XML, JPG ou PNG.`);
        return false;
      }
      if (file.size > maxSize) {
        alert(`Arquivo ${file.name}: Tamanho excede 10MB.`);
        return false;
      }
      return true;
    });
    
    setFiles(prev => [...prev, ...validFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (!hash || files.length === 0) return;
    
    setUploading(true);
    
    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('arquivos', file);
      });
      
      const response = await fetch(`${API_URL}/api/v1/upload-nf/enviar/${hash}`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao enviar arquivos');
      }
      
      const result = await response.json();
      setUploadSuccess(true);
      setFiles([]);
      fetchInfo(); // Recarregar info
      
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-12 w-12 animate-spin text-purple-600 mb-4" />
            <p className="text-muted-foreground">Carregando...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <XCircle className="h-16 w-16 text-red-500 mb-4" />
            <h2 className="text-xl font-bold text-center mb-2">Link Inválido</h2>
            <p className="text-muted-foreground text-center">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!info) return null;

  const isExpired = !info.link_valido && info.status !== 1;
  const alreadyUploaded = info.status === 1 || uploadSuccess;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-purple-700 to-indigo-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-lg shadow-2xl">
        <CardHeader className="text-center border-b">
          <div className="flex items-center justify-center gap-2 mb-2">
            <FileText className="h-8 w-8 text-purple-600" />
            <CardTitle className="text-2xl">Envio de Nota Fiscal</CardTitle>
          </div>
          <CardDescription>
            Faça o upload do arquivo da nota fiscal
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6 pt-6">
          {/* Informações do Lote/Envio */}
          <div className="bg-slate-50 rounded-lg p-4 space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground font-medium">
                {info.tipo === 'prestador' ? 'Prestador:' : 'Montador:'}
              </span>
              <span className="font-semibold">{info.nome}</span>
            </div>
            {info.email && (
              <div className="flex justify-between">
                <span className="text-muted-foreground font-medium">Email:</span>
                <span>{info.email}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground font-medium">
                {info.tipo === 'prestador' ? 'Lote ID:' : 'Envio ID:'}
              </span>
              <span>{info.lote_id || info.envio_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground font-medium">Período:</span>
              <span>{info.periodo}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground font-medium">Valor Total:</span>
              <span className="font-semibold text-green-600">{formatCurrency(info.valor_total)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground font-medium">Quantidade OS:</span>
              <span>{info.quantidade_os}</span>
            </div>
          </div>

          {/* Status */}
          {isExpired && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Este link expirou. Entre em contato para solicitar um novo link.
              </AlertDescription>
            </Alert>
          )}

          {alreadyUploaded && (
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                <strong>Nota fiscal recebida com sucesso!</strong>
                <br />
                Obrigado pelo envio. O pagamento será processado em breve.
              </AlertDescription>
            </Alert>
          )}

          {/* Arquivos já enviados */}
          {info.arquivos_enviados.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">Arquivos Enviados:</h4>
              <div className="space-y-2">
                {info.arquivos_enviados.map((arq, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-green-50 p-2 rounded border border-green-200">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="flex-1 text-sm truncate">{arq.nome}</span>
                    <span className="text-xs text-muted-foreground">{arq.tamanho_formatado}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Área de Upload */}
          {!isExpired && !alreadyUploaded && (
            <>
              <div
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors duration-200
                  ${dragActive 
                    ? 'border-purple-500 bg-purple-50' 
                    : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'}
                `}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input')?.click()}
              >
                <input
                  id="file-input"
                  type="file"
                  multiple
                  accept=".pdf,.xml,.jpg,.jpeg,.png"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 bg-gray-100 rounded-full">
                    <Upload className="h-8 w-8 text-gray-400" />
                  </div>
                  <div>
                    <p className="font-semibold">Selecione os arquivos da Nota Fiscal</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Você pode selecionar múltiplos arquivos de uma vez.
                      <br />
                      Segure Ctrl (Windows) ou Cmd (Mac) para selecionar vários arquivos.
                    </p>
                  </div>
                  <Button variant="outline" type="button">
                    Escolher Arquivos
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Formatos aceitos: PDF, XML, JPG, PNG (máx. 10MB cada) - Múltiplos permitidos
                  </p>
                </div>
              </div>

              {/* Lista de arquivos selecionados */}
              {files.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Arquivos selecionados ({files.length}):</h4>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {files.map((file, idx) => (
                      <div key={idx} className="flex items-center gap-2 bg-slate-50 p-2 rounded border">
                        <File className="h-4 w-4 text-purple-600" />
                        <span className="flex-1 text-sm truncate">{file.name}</span>
                        <span className="text-xs text-muted-foreground">{formatBytes(file.size)}</span>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => removeFile(idx)}
                          className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>

                  <Button 
                    className="w-full mt-4 bg-purple-600 hover:bg-purple-700"
                    size="lg"
                    onClick={handleUpload}
                    disabled={uploading}
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Upload className="mr-2 h-4 w-4" />
                        Enviar {files.length} arquivo{files.length > 1 ? 's' : ''}
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          )}

          {/* Validade do link */}
          {!alreadyUploaded && (
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              {isExpired ? (
                <span className="text-red-500">Link expirado</span>
              ) : (
                <span>Link válido por mais {info.dias_restantes} dia{info.dias_restantes !== 1 ? 's' : ''}</span>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
