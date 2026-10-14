"""
dash_ctrl.py — Controller do Dashboard de Business Intelligence Unificado
"""

import pandas as pd
from controllers import estoque_ctrl

class DashboardController:
    def __init__(self):
        pass

    def obter_dados_vendas_filtrados(self, f_tipo, f_marca, f_tecido, f_corte, f_cor):
        dados = estoque_ctrl.buscar_dados_dashboard(f_tipo, f_marca, f_tecido, f_corte, f_cor)
        df = pd.DataFrame(dados)
        return df

    def calcular_metricas_financeiras(self, df):
        if df.empty: return {"faturamento": 0.0, "gastos_custo": 0.0, "lucro_real": 0.0}
        faturamento = float(df['valor_total'].sum())
        gastos_custo = float((df['preco_custo'] * df['quantidade']).sum())
        return {"faturamento": faturamento, "gastos_custo": gastos_custo, "lucro_real": faturamento - gastos_custo}

    def processar_historico_temporal(self, df, escala_temporal="D"):
        if df.empty: return pd.Series(dtype=float)
        df = df.copy()
        df['data_venda'] = pd.to_datetime(df['data_venda'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['data_venda']).set_index('data_venda').sort_index()
        if escala_temporal == "D":
            df = df[df.index >= (df.index.max() - pd.Timedelta(days=30))]
        try:
            return df['valor_total'].resample(escala_temporal).sum()
        except ValueError:
            return df['valor_total'].resample("ME" if escala_temporal == "M" else "M").sum()

    def processar_dados_estoque_rosca(self):
        dados = estoque_ctrl.buscar_dados_estoque_dashboard()
        df = pd.DataFrame(dados)
        if df.empty: return pd.Series(dtype=int)
        return df.groupby("tipo")["estoque"].sum()

    def processar_demanda_por_corte(self, df):
        if df.empty: return pd.Series(dtype=int)
        return df.groupby("corte")["quantidade"].sum().sort_values(ascending=True)

    def processar_demanda_por_tecido(self, df):
        if df.empty: return pd.Series(dtype=int)
        return df.groupby("tecido")["quantidade"].sum().sort_values(ascending=True)

    def processar_demanda_por_tipo(self, df):
        """Agrupa a quantidade vendida por tipo de peça (Ex: Blusa, Calça)."""
        if df.empty: return pd.Series(dtype=int)
        return df.groupby("tipo")["quantidade"].sum().sort_values(ascending=True)

    def processar_demanda_por_marca(self, df):
        """Agrupa a quantidade vendida por marca (Ex: Nike, Zara)."""
        if df.empty: return pd.Series(dtype=int)
        return df.groupby("marca")["quantidade"].sum().sort_values(ascending=True)
