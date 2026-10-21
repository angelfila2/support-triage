"""Conservative rules for the four documented self-service capabilities.

These are explicit product policies, not a general semantic safety detector.
Unknown capabilities are never authorized merely by embedding similarity.
"""

import re


def has(pattern, text):
    return re.search(pattern, text, re.I | re.S) is not None


def severity_floor(text):
    if has(r"\b(?:breach|severe data loss)\b", text) or (
        has(r"\b(?:entire|whole|all customers|all users|everyone|widespread)\b", text)
        and has(r"\b(?:outage|down|unavailable|inaccessible|cannot|unable|blocked)\b", text)
    ):
        return "SEV1"
    if has(r"\b(?:all employees|multiple users|our company|whole team)\b", text) and has(
        r"\b(?:cannot|unable|blocked|disruption)\b", text
    ):
        return "SEV2"
    return None


def login_progress(text):
    """Count explicitly attempted FAQ steps, excluding explicitly untried clauses."""
    text = text.lower().replace("haven't", "have not").replace("didn't", "did not")
    # Do not count a list introduced by 'have not tried' as attempted steps.
    attempted = re.sub(r"\b(?:have not|has not|did not|not yet|should i|could i|can i|yet to)\b[^.!?\n]*", "", text)
    unresolved = has(r"\b(?:still|persists?|fails?|cannot|can't|no difference|did not fix)\b", text)
    all_steps = has(r"\b(?:all|every)\b.{0,35}\b(?:steps?|troubleshooting)\b", attempted)
    groups = [r"\b(?:another|different|second) browser\b", r"\b(?:cookies?|cache)\b",
              r"\b(?:incognito|private brows\w*|private window)\b",
              r"\b(?:another|different|second) (?:computer|machine|device)\b"]
    attempted_action = has(r"\b(?:tried|trying|tested|completed|performed|followed|attempted|cleared|clearing|used|using|made no difference|did not fix)\b", attempted)
    exhausted = unresolved and attempted_action and (all_steps or all(has(pattern, attempted) for pattern in groups))
    return bool(exhausted)


def capability(text):
    if has(r"\b(?:password|reset link|recovery (?:url|link)|account secret)\b", text):
        return "password_reset", "password_reset.md"
    if has(r"\b(?:invoice|receipt|billing|charges?|charged|refund|proof of payment)\b", text):
        return "billing_question", "billing.md"
    if has(r"\b(?:shipping|shipment|parcel|package|delivery|tracking)\b", text):
        return "shipping_delay", "shipping.md"
    if has(r"\b(?:login|log in|sign in|access works|access still fails)\b", text):
        return "login_issues", "login_issues.md"
    return None, None


def assess_policy(text, context):
    """Return a verified capability, human-only rule, or unsupported status."""
    category, source = capability(text)
    result = dict(category=category, source=source, allowed=False,
                  troubleshooting_exhausted=False, reason="No documented self-service capability matched.")
    if not isinstance(context, str) or not context.strip():
        return {**result, "reason": "No retrieved evidence supports a reply."}
    if severity_floor(text):
        return {**result, "reason": "Critical or major disruption requires human escalation."}
    if has(r"\b(?:hackerrank|claude|visa|delete (?:my |the )?account|remove (?:my |the )?account|cancel (?:my )?subscription|change (?:my )?(?:plan|address|currency))\b", text):
        return {**result, "reason": "Product-specific or account-changing requests are outside the current FAQ capabilities."}
    if has(r"\b(?:api|endpoint|webhook|algorithm|saml|sso|mfa|2fa|certificate|server configuration|token policy|configure|configuration|fingerprint)\b", text):
        return {**result, "reason": "The current FAQ does not document this technical capability."}
    # Refunds and charge investigations cannot be approved by this agent.
    billing_text = re.sub(r"\b(?:not asking for|not requesting|do not want|don't want) (?:a )?refund\b", "", text, flags=re.I)
    if has(r"\b(?:refund|charged twice|duplicate (?:charge|payment)|payment appears twice|unexpected charge)\b", billing_text):
        return {**result, "reason": "Refunds and payment investigations require a human."}
    if category == "billing_question" and has(r"\b(?:wrong|incorrect|unrecognized|unauthoriz\w*|unexpected|disput\w*|fraud\w*|correct|amend|modify|change|update)\b", billing_text):
        return {**result, "reason": "Billing discrepancies require human investigation."}
    if category == "shipping_delay" and has(r"\b(?:change|cancel|reroute|reschedule|redirect|update address)\b", text):
        return {**result, "reason": "Shipment changes are outside the documented self-service capability."}
    if category == "shipping_delay":
        days = re.findall(r"\b(\d+)\s*days?\b", text, re.I)
        stale = has(r"\b(?:not (?:changed|updated|moved)|hasn't (?:changed|updated|moved)|stalled|no (?:updates?|movement))\b", text)
        long_delay = any(int(day) > 5 for day in days) or has(r"\b(?:week|seven|six|eight|nine|ten)\b", text)
        if has(r"\b(?:lost|investigat\w*)\b", text) or (stale and long_delay):
            return {**result, "reason": "Lost shipments or tracking stalled over five days require investigation."}
    if category == "login_issues":
        exhausted = login_progress(text)
        if exhausted:
            return {**result, "troubleshooting_exhausted": True,
                    "reason": "Applicable login troubleshooting has already failed."}
    if category == "password_reset" and has(r"\b(?:neither works|still (?:fails?|broken)|links? (?:do not|don't) work)\b", text):
        return {**result, "troubleshooting_exhausted": True,
                "reason": "Fresh reset links have already failed; investigation is needed."}
    # Require the documented capability as well as a matching ticket topic.
    evidence_markers = {
        "password_reset": r"password reset|reset link",
        "billing_question": r"billing|invoice|receipt",
        "shipping_delay": r"tracking|shipment|delivery",
        "login_issues": r"incognito|cookies|different browser",
    }
    supported_requests = {
        "password_reset": r"reset|forgot|cannot remember|can't remember|recover|expir|valid",
        "billing_question": r"download|copy|receipt|proof of payment|view|see|where|obtain|find|need (?:my |an? |the )?invoice",
        "shipping_delay": r"tracking|status|where|delay|late|hasn't moved|not changed|lost",
        "login_issues": r"cannot|can't|unable|fails?|trouble|access works",
    }
    if category and has(evidence_markers[category], context) and has(supported_requests[category], text):
        return {**result, "allowed": True,
                "reason": "A documented self-service capability applies; human-only rules did not match."}
    return result


def enforce_policy(text, context, assessment):
    """Keep raw model fields for audits; do not upgrade malformed model output."""
    result = dict(assessment)
    result["model_can_auto_reply"] = bool(result.get("model_can_auto_reply", result.get("can_auto_reply")))
    result["model_category"] = result.get("model_category", result.get("category", "other"))
    result["model_troubleshooting_exhausted"] = bool(result.get("model_troubleshooting_exhausted", result.get("troubleshooting_exhausted")))
    policy = assess_policy(text, context)
    result["policy_reason"] = policy["reason"]
    result["category"] = policy["category"] or "other"
    if result.get("confidence", 0) > 0:
        result["can_auto_reply"] = policy["allowed"]
        result["troubleshooting_exhausted"] = (
            policy["troubleshooting_exhausted"] if policy["category"] == "login_issues"
            else policy["troubleshooting_exhausted"] or result["model_troubleshooting_exhausted"]
        )
        result["can_auto_reply"] &= not result["troubleshooting_exhausted"]
    else:
        result["can_auto_reply"] = False
    floor = severity_floor(text)
    if floor and int(result.get("urgency", "SEV3")[-1]) > int(floor[-1]):
        result["urgency"] = floor
    # Known FAQ workflows have explicit service tiers. Never downgrade a
    # critical/major model assessment; those still require human review.
    elif policy["allowed"] and result.get("urgency") in {"SEV3", "SEV4", "SEV5"}:
        if policy["category"] == "login_issues":
            result["urgency"] = "SEV3"
        elif policy["category"] == "billing_question":
            result["urgency"] = "SEV5"
        elif policy["category"] == "password_reset":
            result["urgency"] = "SEV5" if has(r"how (?:long|many)|minutes|lifetime|valid|expire after", text) else "SEV4"
        elif policy["category"] == "shipping_delay":
            result["urgency"] = "SEV4" if has(r"delay|late", text) else "SEV5"
    result["model_reason"] = result.get("model_reason", result.get("reason", ""))
    result["reason"] = policy["reason"] + " " + result["model_reason"]
    return result
