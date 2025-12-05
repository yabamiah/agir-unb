#!/bin/bash
# Script de exemplo para conversão DOCX→PDF usando o utilitário DANI

echo "🔄 Exemplo de uso do utilitário de conversão DOCX→PDF"
echo "=================================================="

# Verificar se o Python está disponível
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale o Python3 primeiro."
    exit 1
fi

# Verificar se o arquivo do utilitário existe
if [ ! -f "convert_docx_to_pdf.py" ]; then
    echo "❌ Arquivo convert_docx_to_pdf.py não encontrado."
    exit 1
fi

echo "📁 Diretórios disponíveis para conversão:"
echo "   - data/dani/docs/output/ (arquivos DOCX do DANI)"
echo "   - data/ (outros arquivos DOCX)"
echo ""

# Exemplo 1: Converter arquivos do DANI
echo "🚀 Exemplo 1: Converter arquivos DOCX do DANI"
echo "Comando: python3 convert_docx_to_pdf.py data/dani/docs/output/ -v"
echo ""
read -p "Deseja executar este exemplo? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Executando conversão dos arquivos do DANI..."
    python3 convert_docx_to_pdf.py data/dani/docs/output/ -v
    echo ""
fi

# Exemplo 2: Converter com diretório de saída específico
echo "🚀 Exemplo 2: Converter com diretório de saída específico"
echo "Comando: python3 convert_docx_to_pdf.py data/dani/docs/output/ -o data/dani/docs/result_pdf/ -w 2"
echo ""
read -p "Deseja executar este exemplo? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Executando conversão com diretório de saída específico..."
    python3 convert_docx_to_pdf.py data/dani/docs/output/ -o data/dani/docs/result_pdf/ -w 2
    echo ""
fi

# Exemplo 3: Mostrar ajuda
echo "📖 Exemplo 3: Mostrar ajuda do utilitário"
echo "Comando: python3 convert_docx_to_pdf.py --help"
echo ""
read -p "Deseja ver a ajuda? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    python3 convert_docx_to_pdf.py --help
    echo ""
fi

echo "✅ Exemplos concluídos!"
echo ""
echo "💡 Dicas de uso:"
echo "   - Use -v para modo verboso (mais informações)"
echo "   - Use -w N para definir número de workers (padrão: 4)"
echo "   - Use -o DIR para definir diretório de saída"
echo "   - O utilitário cria automaticamente subdiretórios 'pdf_output'"
echo ""
echo "🔧 Dependências necessárias:"
echo "   - LibreOffice (recomendado): sudo apt-get install libreoffice"
echo "   - Pandoc (alternativo): sudo apt-get install pandoc"
echo ""
