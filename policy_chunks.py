"""
Chunked policy implementation actions from FAO and OECD for overfishing reduction.
Sources:
  - FAO IPOA-CAP and IUU: https://www.fao.org/4/y3274e/y3274e0f.htm
  - OECD Managing fish stocks sustainably: https://www.oecd.org/.../managing-fish-stocks-sustainably_552926af/60686388-en.pdf
  - OECD Encouraging policy change for sustainable and resilient fisheries: https://www.oecd-ilibrary.org/.../encouraging-policy-change-for-sustainable-and-resilient-fisheries_31f15060-en
"""

POLICY_CHUNKS = [
    # --- FAO IPOA-CAP and IUU (Gréboval) ---
    {
        "content": "Implement the IPOA on Capacity and its provisions for the assessment of fishing capacity and its effective control at national and international levels. Exercise caution in implementing fleet reduction schemes; ensure first that fishing capacity has been brought under effective control through the direct or indirect control of both inputs and outputs.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "implementation_actions",
    },
    {
        "content": "Avoid uncontrolled vessel disposal at international level, especially (a) transfer of vessels to countries that are not effectively implementing the IPOA on fishing capacity and related international instruments and (b) transfer to fisheries recognized by research institutions as overfished. Avoid the use of subsidies which contribute to excess fishing capacity and unsustainability; avoid subsidizing fleet reduction schemes in the absence of prior and effective control on fleet capacity.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "vessel_disposal_subsidies",
    },
    {
        "content": "Establish compatible national records of fishing vessels and support the establishment by FAO of an international record of vessels operating on the high seas. Monitor and assess fishing capacity; in addition to physical characteristics, assess fleet dynamics in terms of investment-disinvestment and deployment (allocation of fishing inputs in time and space and among fisheries). Enhanced monitoring and assessment capabilities should be developed at national, regional and global levels, with emphasis on fleet records and fleet mobility.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "monitoring_assessment",
    },
    {
        "content": "The most appropriate methods for controlling fishing capacity imply strictly controlled and rather exclusive access and a direct or indirect control of both inputs and output. To avoid undesirable IUU reactions: opt for management methods that provide incentive for long-term sustainability (e.g. ITQs); promote enhanced industry participation and co-management; establish clearer responsibilities and answerability; adopt improved MCS methods such as VMS; and account for relationships between fisheries (bio-economic linkages, fleet mobility).",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "management_methods",
    },
    {
        "content": "Control of excess fishing capacity and IUU fishing requires much greater harmonization of management strategies and policies between the main levels: fishery sector, industry segments, and individual fisheries, both at national and international levels. Licence limitation schemes can be effective when input substitution, technological change, and conditions for initial allocation are carefully addressed.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "management_methods",
    },
    {
        "content": "Exercise caution when designing and implementing buyback programmes. Incentive-adjusting schemes (e.g. ITQs) provide incentive for capacity adjustment but not necessarily permanent disposal; incentive-blocking methods do not, and buybacks may lead to a net increase in capacity. Ensure effective control of capacity before promoting reduction. Control export or transfer of capacity outside jurisdiction; prevent transfers to fisheries and areas recognized as significantly overfished.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "fleet_reduction",
    },
    {
        "content": "Ensure no transfer of capacity to the jurisdiction of another State without express consent and formal authorization of that State. Avoid approving transfer of vessels to high seas areas where such transfers are inconsistent with responsible fishing under the Code of Conduct. Strengthen and empower regional fishery organizations; create new organizations for full coverage of resources; encourage non-members to join.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "high_seas_transfers",
    },
    {
        "content": "Assess, reduce and progressively eliminate factors contributing to overcapacity, including subsidies and economic incentives. Shift subsidies from conventional capital to promotion of resource conservation, human skills and institutional development. Provide appropriate support to developing countries (training, technical assistance, financing) for implementation of IPOA-CAP and IPOA-IUU.",
        "source": "FAO",
        "url": "https://www.fao.org/4/y3274e/y3274e0f.htm",
        "topic": "subsidies_support",
    },
    # --- OECD Managing fish stocks sustainably ---
    {
        "content": "Rebuild overfished stocks and harvest all stocks at optimal levels to increase sector profitability, improve environmental sustainability and outcomes for fishing communities. Producing accurate and timely data on the health of fish stocks and how they are managed is fundamental, especially in the face of climate change.",
        "source": "OECD",
        "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/01/managing-fish-stocks-sustainably_552926af/60686388-en.pdf",
        "topic": "rebuild_optimal_harvest",
    },
    {
        "content": "Management regimes combine input controls (fleet and gear characteristics, spatial or temporal restrictions) and output controls (TACs, individual or community quotas, minimum fish sizes). TACs are one of the most important tools for stock health; gear restrictions and TACs are widely used. Governments should rebuild the 18% of stocks that fall below sustainability standards and review management so stocks in good health are fished optimally.",
        "source": "OECD",
        "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/01/managing-fish-stocks-sustainably_552926af/60686388-en.pdf",
        "topic": "management_tools",
    },
    {
        "content": "Invest in stock assessments for stocks not yet assessed and those with inconclusive assessments, particularly for species of significant commercial importance. Develop methods to assess stocks even where data are scarce and capacity limited; this will become more important as climate change impacts abundance and location and requires more frequent assessment.",
        "source": "OECD",
        "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/01/managing-fish-stocks-sustainably_552926af/60686388-en.pdf",
        "topic": "stock_assessment",
    },
    {
        "content": "Link information on stock management and stock health to understand where management is effective and how to optimise fisheries management plans. Adopt an internationally agreed naming convention for reporting stock information, including ASFIS (Aquatic Sciences and Fisheries Information System) species codes where possible.",
        "source": "OECD",
        "url": "https://www.oecd.org/content/dam/oecd/en/publications/reports/2023/01/managing-fish-stocks-sustainably_552926af/60686388-en.pdf",
        "topic": "data_linkage_standards",
    },
    # --- OECD Encouraging policy change for sustainable and resilient fisheries ---
    {
        "content": "Successful fisheries policy change depends on: performance of the sector and its public perception; initiatives by fisheries management officials; legal commitments to adopt changes; better use of data; and effective consultation processes. Macroeconomic and macro-political factors have less impact on fisheries policy than in other policy domains.",
        "source": "OECD",
        "url": "https://www.oecd-ilibrary.org/agriculture-and-food/encouraging-policy-change-for-sustainable-and-resilient-fisheries_31f15060-en",
        "topic": "policy_change_factors",
    },
]


def get_all_chunks():
    """Return list of dicts with keys: content, source, url, topic."""
    return list(POLICY_CHUNKS)
