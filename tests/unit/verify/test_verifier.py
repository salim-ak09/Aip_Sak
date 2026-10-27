from __future__ import annotations

import httpx
import pytest

from venice_pt.contracts.findings import Finding, FindingOrigin, Severity
from venice_pt.verify.verifier import Verifier


@pytest.mark.asyncio
async def test_known_fp_corpus_all_demoted() -> None:
    """SPEC requirement: known-FP corpus (10 planted false positives) -> all demoted."""
    verifier = Verifier()

    # Create 10 false positive candidate findings
    fp_corpus: list[Finding] = []
    for i in range(10):
        cls_type = "sqli" if i % 2 == 0 else "xss"
        fp_corpus.append(
            Finding(
                engagement_id="fp_test",
                title=f"Planted False Positive #{i}",
                cls=cls_type,
                asset_key="asset:127.0.0.1",
                endpoint=f"http://127.0.0.1:3000/safe_page_{i}",
                param="id",
                severity=Severity.HIGH,
                origin=FindingOrigin.KNOWN_TOOL,
                confidence=0.8,
            )
        )

    # Mock client simulating benign responses (no timing delay, encoded reflection)
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "SLEEP" in url_str:
            # Immediate response: no SQLi delay
            return httpx.Response(200, text="Clean benign page")
        if "vptxss" in url_str:
            # Encoded safe reflection: no script execution
            return httpx.Response(200, text="&lt;script&gt;/*canary*/&lt;/script&gt;")
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        for finding in fp_corpus:
            initial_conf = finding.confidence
            verdict = await verifier.check(finding, client=mock_client)
            assert verdict.confirmed is False
            assert finding.verified is False
            # Confidence must be demoted: confidence *= 0.4
            assert finding.confidence == pytest.approx(initial_conf * 0.4, 0.01)


@pytest.mark.asyncio
async def test_known_tp_corpus_all_confirmed() -> None:
    """SPEC requirement: known-TP corpus -> all confirmed."""
    verifier = Verifier()

    tp_sqli = Finding(
        engagement_id="tp_test",
        title="Verified SQL Injection",
        cls="sqli",
        asset_key="asset:127.0.0.1",
        endpoint="http://127.0.0.1:3000/api/search",
        param="q",
        severity=Severity.HIGH,
        origin=FindingOrigin.KNOWN_TOOL,
        confidence=0.7,
    )

    tp_xss = Finding(
        engagement_id="tp_test",
        title="Verified Reflected XSS",
        cls="xss",
        asset_key="asset:127.0.0.1",
        endpoint="http://127.0.0.1:3000/search",
        param="query",
        severity=Severity.MEDIUM,
        origin=FindingOrigin.KNOWN_TOOL,
        confidence=0.7,
    )

    async def mock_tp_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "SLEEP" in url_str:
            import time

            time.sleep(2.6)  # Simulate real time-based delay
            return httpx.Response(200, text="Vulnerable SQL result")
        if "vptxss" in url_str:
            # Direct unescaped reflection
            return httpx.Response(200, text="<div>Result: vptxss<script>/*canary*/</script></div>")
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(mock_tp_handler)
    async with httpx.AsyncClient(transport=transport) as mock_client:
        v_sqli = await verifier.check(tp_sqli, client=mock_client)
        assert v_sqli.confirmed is True
        assert tp_sqli.verified is True
        assert tp_sqli.confidence > 0.7

        v_xss = await verifier.check(tp_xss, client=mock_client)
        assert v_xss.confirmed is True
        assert tp_xss.verified is True
        assert tp_xss.confidence > 0.7
