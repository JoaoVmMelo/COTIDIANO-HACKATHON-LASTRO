# 🎤 PITCH — COTIDIANO

> **Tagline:** *Ninguém aluga um preço por m². A pessoa aluga uma vida.*
> O COTIDIANO é a Laís simulando o seu **cotidiano real** num bairro — e virando o **topo de funil** que entrega leads quentes pra Lastro.

---

## 1. O problema (≈30s)
As pessoas escolhem onde morar olhando o **valor do aluguel** — e descobrem tarde demais que a **vida real** ali sufoca: condomínio caro, 1h30 de trajeto até o trabalho, nenhuma padaria por perto, sem lugar pro cachorro. Resultado: **arrependimento da mudança** e contrato de 30 meses preso.

Do lado das imobiliárias: esse cliente, no começo da jornada, é um **lead frio que se perde** — pesquisando sozinho, sem contato, sem qualificação.

## 2. A solução (≈30s)
O **COTIDIANO** é a **Laís** (IA) que simula como seria a **sua vida** num bairro:
- 💰 **Custo de vida completo** (moradia + condomínio + contas + transporte), com **intervalo de confiança** — estimativa transparente, não "achismo".
- 🛣️ **Trajeto real** (por ruas) até o **seu** trabalho — não um endereço genérico.
- 🗺️ **A rotina concreta:** a padaria que abre às 6h, o petshop e a praça pro cachorro, o almoço perto do escritório — **com nomes reais** dos lugares.
- 🎯 Um **Score de compatibilidade (0–100)** ponderado pelo seu perfil (tem pet? filhos? vai de metrô?).

Dois modos: **ela te recomenda** o bairro ideal, ou **você dá um local** e ela conta como seria viver ali. No fim, gera um **relatório personalizado** → você deixa o contato → **vira lead.**

## 3. Roteiro de DEMO ao vivo (≈60s) — o que clicar

> Tenha o servidor rodando: `python -m uvicorn server:app --reload --port 8000`

1. **"Fale com a Laís"** → preencha: orçamento **R$ 5.000**, **trabalho: "Av. Faria Lima 1500"**, estilo "bares e parques" → **Recomendar meu bairro**.
   - *Fala:* "Repara: ela ranqueia os bairros perto do **meu** trabalho real, dentro do **meu** orçamento."
2. **No chat, digite:** *"e se meu orçamento caísse pra 3.500?"* → ela **recalcula ao vivo**.
   - *Fala:* "Isso é o pulo do gato: a Laís **executa o motor de cálculo de verdade** — quando mudo de ideia, ela recomputa os números reais. Não é um chatbot que decora resposta."
3. **"Já tenho um local"** → escolha **Pinheiros**, trabalho **Faria Lima**, marque **pet + filhos**, orçamento.
   - Mostre o **Score 90+/100** com as barras, o **mapa** (casa, trabalho, rotas, comércio colorido) e a **rotina**: ☕ padaria → 💼 *"pro almoço, o Zé da Prata a 390m do escritório"* → 🐶 petshop + praça → 🍽️ restaurante. **Tudo com nome real.**
4. **"Quero o relatório"** → deixe nome + contato → **relatório gerado por IA aparece**.
   - *Fala:* "Esse contato não é um lead frio: chega na Laís da Lastro **já sabendo** orçamento, onde trabalha, estilo de vida e os bairros que considerou."

## 4. Impacto no negócio (pra Lastro) — o que pontua
A Laís da Lastro **converte** leads. O COTIDIANO **gera leads melhores pra ela converter.**
- É **aquisição / topo de funil:** a pessoa usa de graça, se engaja e **deixa o contato** pelo relatório.
- O lead chega **pré-qualificado e rico em intenção** → corretor perde menos tempo, conversão sobe.
- **Modelo:** widget embedável no site da imobiliária parceira → **gera lead passivamente**.

## 5. Viabilidade (o outro critério)
- **Roda hoje, ponta a ponta**, com **fallback offline** — o demo **não quebra** (sem internet, vira texto-modelo).
- Stack enxuta e **sem custo de dados:** OpenStreetMap (locais), OSRM (rotas), Nominatim (geocoding) — **grátis, sem chave**.
- **Honestidade como força:** custo é **estimativa de amostra com intervalo de confiança**, nunca "valor oficial". Isso é maturidade, não fraqueza.
- **Escalável:** OSM/OSRM são globais → replicável pra qualquer cidade.

## 6. Diferenciação (1 linha)
> "Os portais te mostram **imóveis**. O COTIDIANO te mostra **a sua vida** naquele lugar."

## 7. Evolução / visão (mostra que não é só hackathon)
- **Dados:** Google Places (avaliações/horários), **GTFS da SPTrans** (trajeto de ônibus real), e um **dataset próprio de custo** via crowdsource ("quanto você paga?") → vira **moat**.
- **Verticais:** relocação corporativa, estudantes, famílias.

## 8. Defesa — perguntas que os jurados vão fazer
- **"Os preços são confiáveis?"** → "São **estimativas** de uma amostra de anúncios, **sempre com intervalo de confiança** — somos transparentes. A **localização** (OSM) e os **trajetos** (OSRM) são reais. Em produção, plugamos dados oficiais."
- **"Qual a diferença do QuintoAndar/ZAP?"** → "Eles listam imóveis. A gente entrega **decisão**: commute real até o seu trabalho, rotina concreta, custo total. É a camada que falta."
- **"Por que a Laís e não um chatbot qualquer?"** → "Ela é **agêntica**: executa o código e recalcula ao vivo, não decora. E é o **top de funil** da Laís de produção da Lastro."
- **"Como escala / como ganha?"** → "Aquisição B2B2C: widget pras imobiliárias. Dados globais e grátis (OSM) → replicável em qualquer cidade."

---

## ▶️ O ROTEIRO FALADO (2 min, pronto pra ler)

> "Quando alguém vai mudar de casa, decide pelo **valor do aluguel**. E aí descobre tarde demais que a **vida real** naquele bairro sufoca: condomínio caro, uma hora e meia de trânsito, nenhuma padaria por perto. A pessoa se arrepende — e fica presa num contrato de 30 meses.
>
> O problema é que ninguém aluga um preço por metro quadrado. **A pessoa aluga uma vida.** Os portais mostram imóveis; ninguém mostra como seria o seu **cotidiano** ali.
>
> É isso que o **COTIDIANO** faz. É a **Laís**, uma IA que simula a sua vida num bairro: o custo de vida completo — com intervalo de confiança, porque a gente é honesto que é estimativa —, o **trajeto real** até o **seu** trabalho, e a rotina concreta: a padaria que abre às seis, o petshop pro cachorro, o almoço perto do escritório. Tudo com nome real e um **Score de compatibilidade** com o seu perfil.
>
> *(demo)* Eu digo onde trabalho, e ela me recomenda os bairros que cabem no meu bolso e perto de mim. Se eu mudo de ideia no chat — 'e se fosse 3.500?' — ela **recalcula na hora**, porque ela executa o cálculo de verdade, não decora resposta. E quando eu gosto, eu deixo meu contato pra receber o **relatório completo**.
>
> E é aqui que está o valor pra Lastro: esse contato vira um **lead quente**. A Laís de vocês **converte** leads — o COTIDIANO **gera leads melhores pra ela converter**, já sabendo orçamento, trabalho e estilo de vida da pessoa. É o **topo de funil** que faltava.
>
> Roda hoje, de graça, com dados reais de localização e rota. Os portais mostram imóveis. **A gente mostra a sua vida.**"
