import os
import sys
import json
import re
from github import Github, Auth
from google import genai

def main():
    # 1. Recupera le variabili d'ambiente passate dalla GitHub Action
    github_token = os.environ.get("GITHUB_TOKEN")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    pr_number_str = os.environ.get("PR_NUMBER")

    if not all([github_token, gemini_api_key, repo_name, pr_number_str]):
        print("Errore: Variabili d'ambiente mancanti. Controlla il workflow YAML.")
        sys.exit(1)
        
    pr_number = int(pr_number_str)

    # 2. Inizializza i client di GitHub e Gemini (usando il metodo aggiornato per l'Auth)
    auth = Auth.Token(github_token)
    gh = Github(auth=auth)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    client = genai.Client(api_key=gemini_api_key)

    # 3. Estrai le modifiche calcolando i numeri di riga reali
    print("Recupero le modifiche della PR con mappatura delle righe...")
    diff_text = ""
    for file in pr.get_files():
        # Ignoriamo i file lock per risparmiare token ed evitare rumore
        if file.filename.endswith(("package-lock.json", "yarn.lock", "poetry.lock")):
            continue
        
        if file.patch:
            diff_text += f"--- File: {file.filename} ---\n"
            patch_lines = file.patch.split('\n')
            current_line = 0
            
            for line in patch_lines:
                # Intercetta l'header del diff per trovare la riga di partenza (es: @@ -10,5 +10,8 @@)
                match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                if match:
                    current_line = int(match.group(1))
                    diff_text += f"{line}\n"
                elif line.startswith('+'):
                    # Riga aggiunta o modificata: numeriamola
                    diff_text += f"[{current_line}] {line}\n"
                    current_line += 1
                elif line.startswith('-'):
                    # Riga rimossa: a GitHub non interessa per i nuovi commenti
                    diff_text += f"{line}\n"
                elif line.startswith(' '):
                    # Riga di contesto: numeriamola per far avanzare il contatore
                    diff_text += f"[{current_line}] {line}\n"
                    current_line += 1
                else:
                    diff_text += f"{line}\n"
                    
            diff_text += "\n"

    if not diff_text.strip():
        print("Nessuna modifica testuale rilevante da analizzare. Esco.")
        sys.exit(0)

    # 4. Prompt per forzare JSON e fargli usare i numeri di riga tra parentesi quadre
    prompt = f"""
Agisci come un Senior Software Engineer e fai una code review della seguente Pull Request.
Il codice che ti fornisco ha i numeri di riga effettivi tra parentesi quadre all'inizio della riga (es: [15] + const a = 1;).

Restituisci la tua risposta ESCLUSIVAMENTE in un formato JSON valido con questa esatta struttura, senza aggiungere testo fuori dal JSON:
{{
  "summary": "Un riassunto generale della PR, spiegando le modifiche principali e suggerimenti globali.",
  "inline_comments": [
    {{
      "path": "percorso/del/file.estensione",
      "line": numero_di_riga_intero_estratto_dalle_parentesi_quadre,
      "comment": "Il tuo suggerimento per questa specifica riga. Concentrati su bug, sicurezza e clean code."
    }}
  ]
}}

Regole cruciali per il JSON:
1. 'line' DEVE ESSERE ESATTAMENTE il numero che leggi tra le parentesi quadre [ ] all'inizio della riga che vuoi commentare. Non inventare numeri.
2. Fai commenti solo sulle righe che iniziano con [+] (codice aggiunto/modificato) e che hanno un numero tra parentesi quadre.
3. Se non ci sono appunti specifici sulle righe, lascia l'array 'inline_comments' vuoto [].

Ecco il codice:
{diff_text}
"""

    # 5. Chiama Gemini e fai il parsing del JSON
    print("Analisi del codice con Gemini in corso...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # Pulizia della risposta in caso Gemini aggiunga i backtick del markdown
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:-3]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:-3]
            
        data = json.loads(raw_text.strip())
    except Exception as e:
        print(f"Errore API Gemini o parsing JSON fallito: {e}")
        print(f"Risposta grezza ricevuta:\n{response.text if 'response' in locals() else 'Nessuna risposta'}")
        sys.exit(1)

    summary = data.get("summary", "Nessun riassunto generato.")
    inline_comments = data.get("inline_comments", [])
    
    # Per i commenti inline, serve l'ultimo commit della PR
    commits = list(pr.get_commits())
    last_commit = commits[-1]
    
    failed_inline_comments = []
    
    # 6. Pubblica i commenti INLINE (riga per riga)
    print(f"Trovati {len(inline_comments)} commenti inline da pubblicare...")
    for comment in inline_comments:
        try:
            path = comment.get("path")
            line = comment.get("line")
            body = comment.get("comment")
            
            if not all([path, line, body]):
                continue
                
            pr.create_review_comment(
                body=f"🤖 **Gemini AI:** {body}",
                commit=last_commit,
                path=path,
                line=int(line),
                side="RIGHT"
            )
            print(f"  -> Successo: Commento aggiunto su {path} riga {line}")
        except Exception as e:
            # Se GitHub rifiuta la riga (es. non fa parte del diff), intercettiamo l'errore
            print(f"  -> Fallito su {path}:{line}. Verrà spostato nel riassunto. Errore: {e}")
            failed_inline_comments.append(comment)

    # 7. Pubblica il RIASSUNTO GENERALE
    main_review_body = f"🤖 **Gemini AI Review Summary**\n\n{summary}\n"
    
    # Accodiamo i commenti inline che GitHub ha rifiutato, per non perderli
    if failed_inline_comments:
        main_review_body += "\n---\n### ⚠️ Feedback Aggiuntivi\n"
        for fc in failed_inline_comments:
            main_review_body += f"- **File:** `{fc.get('path')}` (Riga {fc.get('line')}): {fc.get('comment')}\n"

    print("Pubblicazione della review generale in corso...")
    try:
        pr.create_review(
            body=main_review_body,
            event="COMMENT" 
        )
        print("Workflow completato con successo!")
    except Exception as e:
        print(f"Errore durante la pubblicazione della review principale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()