import io
import pandas as pd
from fastapi.responses import Response

def generate_csv_response(sondage_obj) -> Response:
    """
    Convertit l'objet SondageComplet en CSV via Pandas et retourne une FastAPI Response.
    """
    records = sondage_obj.to_flat_dataframe_records()
    if not records:
        df = pd.DataFrame(columns=[
            "Campus", "Formation", "Semestre", "Annee_Scolaire", 
            "Section", "Question_ID", "Question", "Type_Question", 
            "Categorie", "Reponse_ID", "Valeur_Reponse"
        ])
    else:
        df = pd.DataFrame(records)
        
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep=";", encoding="utf-8-sig")
    
    filename = f"export_{sondage_obj.formation}_{sondage_obj.semestre}.csv"
    
    return Response(
        content=csv_buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
