import os
import requests
import subprocess
import shutil
from googleapiclient.discovery import build

# --- CONFIGURAÇÕES ---
SHEET_ID = '1X1-DvnnlEirygGW3x7r7U2iw-FWTw95oICv4zCqQHhM'
API_KEY = 'AIzaSyCz9hvz0H1q1-qlnUAEDy0kVTZbcMaCZp0'
REPO_REMOTO = "https://github.com/Pecorine125/Projetos.git"

# Credenciais de Acesso
USUARIO_MESTRE = "admin"
SENHA_MESTRE = "123"

# Mapeamento de Abas -> Pastas
CONFIG_PASTAS = {
    "Geral -18": "Pecorine125/Projetos/Geral -18/",
    "Geral +18": "Pecorine125/Projetos/Geral +18/",
    "Progresso": "Pecorine125/Projetos/ProgressBar/"
}

def configurar_git_inicial():
    """Configura o Git localmente e garante que o remote está correto."""
    if not os.path.exists(".git"):
        print("\n[GIT] Inicializando repositório...")
        subprocess.run("git init", shell=True)
    
    # Tenta adicionar o remote, se já existir ele apenas atualiza
    subprocess.run(f"git remote add origin {REPO_REMOTO}", shell=True)
    subprocess.run(f"git remote set-url origin {REPO_REMOTO}", shell=True)
    
    # Configurações de identidade
    subprocess.run('git config user.name "Pecorine125 Bot"', shell=True)
    subprocess.run('git config user.email "bot@pecorine.com"', shell=True)
    subprocess.run('git config credential.helper store', shell=True)

def baixar_arquivo(url, caminho_destino, nome_arquivo):
    """Faz o download e salva temporariamente."""
    if not os.path.exists(caminho_destino):
        os.makedirs(caminho_destino)

    # Limpeza da extensão e nome
    extensao = url.split('.')[-1].split('?')[0]
    if len(extensao) > 4: extensao = "bin" # Fallback para links sem extensão clara
    
    nome_limpo = "".join([c for c in nome_arquivo if c.isalnum() or c in (' ', '-', '_')]).strip()
    caminho_completo = os.path.join(caminho_destino, f"{nome_limpo}.{extensao}")

    try:
        print(f"   -> Baixando: {nome_limpo}...")
        resposta = requests.get(url, timeout=20, stream=True)
        
        if resposta.status_code == 404:
            print(f"   [AVISO] Link quebrado (404): {nome_limpo}")
            return False
            
        resposta.raise_for_status()
        with open(caminho_completo, 'wb') as f:
            for chunk in resposta.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"   [ERRO] Falha ao baixar {nome_limpo}: {e}")
        return False

def processar_planilha():
    configurar_git_inicial()
    
    print("\n" + "="*30)
    print(" SELECIONE O QUE SINCRONIZAR")
    print("="*30)
    print("1 - Apenas Geral -18")
    print("2 - Apenas Geral +18")
    print("3 - Apenas Progresso (ProgressBar)")
    print("4 - TUDO (Todas as abas)")
    print("0 - Sair")
    
    opcao = input("\nEscolha uma opção: ")

    abas_selecionadas = {}
    if opcao == "1": abas_selecionadas = {"Geral -18": CONFIG_PASTAS["Geral -18"]}
    elif opcao == "2": abas_selecionadas = {"Geral +18": CONFIG_PASTAS["Geral +18"]}
    elif opcao == "3": abas_selecionadas = {"Progresso": CONFIG_PASTAS["Progresso"]}
    elif opcao == "4": abas_selecionadas = CONFIG_PASTAS
    elif opcao == "0": return
    else:
        print("Opção inválida."); return

    service = build('sheets', 'v4', developerKey=API_KEY)
    total_baixado = 0

    for aba, pasta in abas_selecionadas.items():
        print(f"\n[LENDO] Aba: {aba}")
        try:
            result = service.spreadsheets().values().get(spreadsheetId=SHEET_ID, range=f"{aba}!A2:C").execute()
            linhas = result.get('values', [])

            for linha in linhas:
                if len(linha) >= 2 and linha[1].startswith('http'):
                    if baixar_arquivo(linha[1], pasta, linha[0]):
                        total_baixado += 1
        except Exception as e:
            print(f"Erro na aba {aba}: {e}")

    if total_baixado > 0:
        print(f"\n[GIT] {total_baixado} arquivos novos. Preparando envio...")
        
        # Identifica a branch atual (master ou main)
        branch_atual = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True).decode().strip()
        
        subprocess.run("git add .", shell=True)
        subprocess.run(f'git commit -m "Upload: {total_baixado} arquivos via script"', shell=True)
        
        print(f"[GIT] Enviando para branch: {branch_atual}...")
        push = subprocess.run(f"git push origin {branch_atual}", shell=True)

        if push.returncode == 0:
            print("\n[OK] Sincronização concluída com sucesso!")
            if os.path.exists("Pecorine125"):
                shutil.rmtree("Pecorine125")
                print("Pasta temporária removida. PC limpo.")
        else:
            print("\n[ERRO] O Push falhou. Verifique se você tem permissão de escrita no repositório.")
    else:
        print("\nNenhum arquivo novo para processar.")

if __name__ == "__main__":
    print("--- LOGIN DE SEGURANÇA ---")
    u = input("Usuário: ")
    s = input("Senha: ")

    if u == USUARIO_MESTRE and s == SENHA_MESTRE:
        processar_planilha()
    else:
        print("Acesso Negado.")