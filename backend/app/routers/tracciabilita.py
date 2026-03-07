"""Router per la tracciabilita' completa della filiera olio."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lotto_sql import LottoOlio
from app.models.raccolta_sql import Raccolta, RaccoltaParcella
from app.models.parcella_sql import Parcella
from app.models.confezionamento_sql import Confezionamento, ConfezionamentoLotto
from app.models.vendita_sql import Vendita, VenditaRiga
from app.models.cliente_sql import Cliente
from app.models.contenitore_sql import Contenitore
from app.models.frantoio_sql import Frantoio
from app.models.movimento_magazzino_sql import MovimentoMagazzino
from app.core.security import get_current_user
from sqlalchemy import func, case


router = APIRouter(prefix="/tracciabilita", tags=["tracciabilita"])


def _cliente_denominazione(c):
    """Restituisce la denominazione del cliente."""
    if c.tipo_cliente == "azienda":
        return c.ragione_sociale or "—"
    return f"{c.cognome or ''} {c.nome or ''}".strip() or "—"


def _build_catena_lotto(lotto_id: int, db: Session) -> dict:
    """Costruisce la catena di tracciabilita' completa per un lotto."""
    lotto = db.query(LottoOlio).filter(LottoOlio.id == lotto_id).first()
    if not lotto:
        return None

    # --- MONTE: Raccolta e Parcelle ---
    raccolta = db.query(Raccolta).filter(Raccolta.id == lotto.raccolta_id).first()
    parcelle_info = []
    if raccolta:
        rp_rows = (
            db.query(RaccoltaParcella, Parcella)
            .join(Parcella, RaccoltaParcella.parcella_id == Parcella.id)
            .filter(RaccoltaParcella.raccolta_id == raccolta.id)
            .all()
        )
        for rp, p in rp_rows:
            parcelle_info.append({
                "id": p.id,
                "codice": p.codice,
                "nome": p.nome,
                "varieta": p.varieta_principale,
                "superficie_ettari": float(p.superficie_ettari),
                "kg_olive": float(rp.kg_olive),
            })

    # Frantoio
    frantoio_info = None
    if lotto.frantoio_id:
        fr = db.query(Frantoio).filter(Frantoio.id == lotto.frantoio_id).first()
        if fr:
            frantoio_info = {"id": fr.id, "denominazione": fr.denominazione, "citta": fr.citta}

    # --- VALLE: Confezionamenti ---
    cl_rows = (
        db.query(ConfezionamentoLotto, Confezionamento)
        .join(Confezionamento, ConfezionamentoLotto.confezionamento_id == Confezionamento.id)
        .filter(ConfezionamentoLotto.lotto_id == lotto.id)
        .order_by(Confezionamento.codice)
        .all()
    )

    # Pre-carica contenitori per i confezionamenti
    cont_ids = list({c.contenitore_id for _, c in cl_rows if c.contenitore_id})
    cont_map = {}
    if cont_ids:
        for ct in db.query(Contenitore).filter(Contenitore.id.in_(cont_ids)).all():
            cont_map[ct.id] = ct.descrizione

    confezionamenti_info = []
    conf_ids = []
    for cl, conf in cl_rows:
        conf_ids.append(conf.id)
        confezionamenti_info.append({
            "id": conf.id,
            "codice": conf.codice,
            "data_confezionamento": conf.data_confezionamento.isoformat() if conf.data_confezionamento else None,
            "formato": conf.formato,
            "contenitore": cont_map.get(conf.contenitore_id, conf.formato),
            "num_unita": conf.num_unita,
            "capacita_litri": float(conf.capacita_litri),
            "litri_totali": float(conf.litri_totali),
            "litri_da_lotto": float(cl.litri_utilizzati),
            "prezzo_listino": float(conf.prezzo_listino) if conf.prezzo_listino else None,
        })

    # --- MAGAZZINO: Giacenze per ogni confezionamento ---
    giacenze_map = {}
    if conf_ids:
        giac_rows = (
            db.query(
                MovimentoMagazzino.confezionamento_id,
                func.sum(
                    case(
                        (MovimentoMagazzino.tipo_movimento == "carico", MovimentoMagazzino.quantita),
                        else_=0,
                    )
                ).label("carichi"),
                func.sum(
                    case(
                        (MovimentoMagazzino.tipo_movimento == "scarico", MovimentoMagazzino.quantita),
                        else_=0,
                    )
                ).label("scarichi"),
            )
            .filter(MovimentoMagazzino.confezionamento_id.in_(conf_ids))
            .group_by(MovimentoMagazzino.confezionamento_id)
            .all()
        )
        for conf_id_g, carichi, scarichi in giac_rows:
            giacenze_map[conf_id_g] = {
                "carichi": int(carichi),
                "scarichi": int(scarichi),
                "giacenza": int(carichi) - int(scarichi),
            }

    # Arricchisci confezionamenti con dati giacenza
    for c in confezionamenti_info:
        g = giacenze_map.get(c["id"], {"carichi": 0, "scarichi": 0, "giacenza": 0})
        c["mag_carichi"] = g["carichi"]
        c["mag_scarichi"] = g["scarichi"]
        c["mag_giacenza"] = g["giacenza"]

    # --- VALLE: Vendite (da confezionamenti di questo lotto) ---
    vendite_info = []
    if conf_ids:
        vr_rows = (
            db.query(VenditaRiga, Vendita, Cliente)
            .join(Vendita, VenditaRiga.vendita_id == Vendita.id)
            .join(Cliente, Vendita.cliente_id == Cliente.id)
            .filter(VenditaRiga.confezionamento_id.in_(conf_ids))
            .order_by(Vendita.data_vendita)
            .all()
        )
        for vr, v, cli in vr_rows:
            vendite_info.append({
                "vendita_id": v.id,
                "vendita_codice": v.codice,
                "data_vendita": v.data_vendita.isoformat() if v.data_vendita else None,
                "stato": v.stato,
                "cliente_id": cli.id,
                "cliente_denominazione": _cliente_denominazione(cli),
                "cliente_citta": cli.citta,
                "confezionamento_id": vr.confezionamento_id,
                "quantita": vr.quantita,
                "importo_riga": float(vr.importo_riga),
            })

    # --- Riepilogo numerico ---
    totale_litri_confezionati = sum(c["litri_da_lotto"] for c in confezionamenti_info)
    totale_unita_vendute = sum(v["quantita"] for v in vendite_info)
    totale_fatturato = sum(v["importo_riga"] for v in vendite_info)
    totale_giacenza_unita = sum(c["mag_giacenza"] for c in confezionamenti_info)
    totale_giacenza_litri = round(sum(c["mag_giacenza"] * c["capacita_litri"] for c in confezionamenti_info), 2)

    return {
        "lotto": {
            "id": lotto.id,
            "codice_lotto": lotto.codice_lotto,
            "anno_campagna": lotto.anno_campagna,
            "data_molitura": lotto.data_molitura.isoformat() if lotto.data_molitura else None,
            "kg_olive": float(lotto.kg_olive),
            "litri_olio": float(lotto.litri_olio),
            "resa_percentuale": float(lotto.resa_percentuale) if lotto.resa_percentuale else None,
            "tipo_olio": lotto.tipo_olio,
            "certificazione": lotto.certificazione,
            "stato": lotto.stato,
            "frantoio": frantoio_info,
        },
        "raccolta": {
            "id": raccolta.id,
            "codice": raccolta.codice,
            "data_raccolta": raccolta.data_raccolta.isoformat() if raccolta.data_raccolta else None,
            "kg_olive_totali": float(raccolta.kg_olive_totali),
            "metodo_raccolta": raccolta.metodo_raccolta,
            "maturazione": raccolta.maturazione,
        } if raccolta else None,
        "parcelle": parcelle_info,
        "confezionamenti": confezionamenti_info,
        "vendite": vendite_info,
        "riepilogo": {
            "litri_olio_totali": float(lotto.litri_olio),
            "litri_confezionati": round(totale_litri_confezionati, 2),
            "litri_disponibili": round(float(lotto.litri_olio) - totale_litri_confezionati, 2),
            "num_confezionamenti": len(confezionamenti_info),
            "num_vendite": len(vendite_info),
            "unita_vendute": totale_unita_vendute,
            "fatturato": round(totale_fatturato, 2),
            "giacenza_unita": totale_giacenza_unita,
            "giacenza_litri": totale_giacenza_litri,
        },
    }


@router.get("/lotto/{lotto_id}")
def tracciabilita_lotto(lotto_id: int, db: Session = Depends(get_db)):
    """Restituisce la catena di tracciabilita' completa per un lotto."""
    result = _build_catena_lotto(lotto_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Lotto non trovato.")
    return result


@router.get("/lotti")
def lista_lotti_tracciabili(
    anno: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Restituisce la lista dei lotti con indicatori di tracciabilita'."""
    query = db.query(LottoOlio)
    if anno:
        query = query.filter(LottoOlio.anno_campagna == anno)
    query = query.order_by(LottoOlio.anno_campagna.desc(), LottoOlio.codice_lotto)
    lotti = query.all()

    # Pre-calcola litri confezionati per ogni lotto
    from sqlalchemy import func
    utilizzo_rows = (
        db.query(
            ConfezionamentoLotto.lotto_id,
            func.sum(ConfezionamentoLotto.litri_utilizzati).label("utilizzati"),
            func.count(ConfezionamentoLotto.id).label("num_conf"),
        )
        .group_by(ConfezionamentoLotto.lotto_id)
        .all()
    )
    utilizzo_map = {row.lotto_id: {"litri": float(row.utilizzati), "num": int(row.num_conf)} for row in utilizzo_rows}

    result = []
    for l in lotti:
        uso = utilizzo_map.get(l.id, {"litri": 0, "num": 0})
        litri_olio = float(l.litri_olio)
        perc = round(uso["litri"] / litri_olio * 100, 1) if litri_olio > 0 else 0
        result.append({
            "id": l.id,
            "codice_lotto": l.codice_lotto,
            "anno_campagna": l.anno_campagna,
            "tipo_olio": l.tipo_olio,
            "litri_olio": litri_olio,
            "litri_confezionati": uso["litri"],
            "percentuale_confezionato": perc,
            "num_confezionamenti": uso["num"],
            "stato": l.stato,
        })
    return result


@router.get("/lotto/{lotto_id}/pdf")
def tracciabilita_lotto_pdf(lotto_id: int, db: Session = Depends(get_db)):
    """Genera il PDF della scheda di tracciabilita' per un lotto."""
    from app.services.pdf_tracciabilita import genera_tracciabilita_pdf

    result = _build_catena_lotto(lotto_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Lotto non trovato.")

    pdf_bytes = genera_tracciabilita_pdf(result, db=db)
    codice = result["lotto"]["codice_lotto"].replace("/", "-")
    filename = f"Tracciabilita_{codice}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
