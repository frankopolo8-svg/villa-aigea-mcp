"""
Hotel AI Brain — Explainable MVP decision engine for hotel demos.

Runs with Python 3.10+ and uses only the standard library.

Core principle:
- Deterministic rules and scores decide what matters.
- A language model may later phrase responses, but it should not make
  irreversible operational decisions by itself.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class ApprovalLevel(str, Enum):
    AUTO = "auto"
    APPROVAL_REQUIRED = "approval_required"
    HUMAN_ONLY = "human_only"


class DecisionType(str, Enum):
    ROOM_READINESS = "room_readiness"
    GUEST_RECOVERY = "guest_recovery"
    UPSELL = "upsell"
    VIP_ARRIVAL = "vip_arrival"
    MAINTENANCE = "maintenance"


@dataclass
class Decision:
    id: str
    decision_type: DecisionType
    title: str
    guest_id: str | None
    room: str | None
    priority: float
    urgency: float
    impact: float
    confidence: float
    approval_level: ApprovalLevel
    reason: str
    recommended_actions: list[dict[str, Any]]
    evidence: list[str]
    estimated_value_eur: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["decision_type"] = self.decision_type.value
        data["approval_level"] = self.approval_level.value
        return data


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def hours_until(now: datetime, value: str | None) -> float:
    if not value:
        return 999.0
    return (parse_dt(value) - now).total_seconds() / 3600


def urgency_from_hours(hours: float, horizon: float = 24.0) -> float:
    if hours <= 0:
        return 100.0
    return clamp(100.0 * (1.0 - min(hours, horizon) / horizon))


def weighted_priority(urgency: float, impact: float, confidence: float) -> float:
    # Priority is deliberately explainable and stable for demos.
    return round(clamp(0.45 * urgency + 0.35 * impact + 0.20 * confidence), 1)


NEGATIVE_TERMS = {
    "noise": 18, "noisy": 18, "dirty": 22, "unclean": 22,
    "late": 10, "waiting": 10, "bad": 10, "terrible": 24,
    "θόρυβ": 18, "βρώμ": 22, "καθυστ": 10, "απαράδεκ": 24,
    "problem": 12, "complaint": 18, "angry": 22,
}

POSITIVE_TERMS = {
    "great": 8, "excellent": 12, "thank": 6, "love": 8,
    "τέλει": 10, "ευχαριστ": 6, "υπέροχ": 10,
}


def sentiment_score(messages: Iterable[str]) -> float:
    """Returns roughly -100 (very negative) to +100 (very positive)."""
    score = 0.0
    for message in messages:
        text = message.lower()
        for term, weight in NEGATIVE_TERMS.items():
            if term in text:
                score -= weight
        for term, weight in POSITIVE_TERMS.items():
            if term in text:
                score += weight
    return clamp(score, -100.0, 100.0)


class HotelBrain:
    def __init__(self, state: dict[str, Any]):
        self.state = state
        self.now = parse_dt(state["now"])
        self.guests = {g["id"]: g for g in state.get("guests", [])}
        self.rooms = {r["number"]: r for r in state.get("rooms", [])}
        self.offers = state.get("offers", [])
        self.policies = state.get("policies", {})

    def analyze(self) -> list[Decision]:
        decisions: list[Decision] = []
        decisions.extend(self._room_readiness_decisions())
        decisions.extend(self._guest_recovery_decisions())
        decisions.extend(self._upsell_decisions())
        decisions.extend(self._vip_decisions())
        decisions.extend(self._maintenance_decisions())
        return sorted(decisions, key=lambda d: d.priority, reverse=True)

    def _room_readiness_decisions(self) -> list[Decision]:
        results: list[Decision] = []
        risky_statuses = {"dirty", "cleaning", "inspection", "blocked"}

        for room in self.rooms.values():
            guest_id = room.get("next_guest_id")
            if not guest_id or room.get("status") not in risky_statuses:
                continue

            guest = self.guests.get(guest_id, {})
            arrival_h = hours_until(self.now, guest.get("arrival"))
            urgency = urgency_from_hours(arrival_h, horizon=8)
            status_points = {
                "dirty": 80, "cleaning": 55, "inspection": 30, "blocked": 100
            }.get(room.get("status"), 20)

            impact = clamp(
                status_points
                + (12 if guest.get("vip") else 0)
                + (10 if guest.get("early_checkin_requested") else 0)
            )
            confidence = 96.0
            priority = weighted_priority(urgency, impact, confidence)

            evidence = [
                f"Άφιξη σε {arrival_h:.1f} ώρες",
                f"Κατάσταση δωματίου: {room.get('status')}",
            ]
            if guest.get("vip"):
                evidence.append("VIP επισκέπτης")
            if guest.get("early_checkin_requested"):
                evidence.append("Έχει ζητηθεί early check-in")

            actions = [
                {
                    "type": "create_housekeeping_task",
                    "label": "Ανάθεση άμεσου καθαρισμού",
                    "payload": {"room": room["number"], "priority": "urgent"},
                    "approval": ApprovalLevel.AUTO.value,
                },
                {
                    "type": "notify_front_desk",
                    "label": "Ενημέρωση reception",
                    "payload": {"room": room["number"], "guest_id": guest_id},
                    "approval": ApprovalLevel.AUTO.value,
                },
            ]
            if arrival_h < 1.5:
                actions.append({
                    "type": "draft_guest_message",
                    "label": "Προετοιμασία ενημέρωσης επισκέπτη",
                    "payload": {
                        "template": "room_delay",
                        "guest_id": guest_id,
                        "language": guest.get("language", "en"),
                    },
                    "approval": ApprovalLevel.APPROVAL_REQUIRED.value,
                })

            results.append(Decision(
                id=f"room-{room['number']}-{guest_id}",
                decision_type=DecisionType.ROOM_READINESS,
                title=f"Κίνδυνος καθυστέρησης δωματίου {room['number']}",
                guest_id=guest_id,
                room=room["number"],
                priority=priority,
                urgency=round(urgency, 1),
                impact=round(impact, 1),
                confidence=confidence,
                approval_level=ApprovalLevel.AUTO,
                reason=(
                    f"Το δωμάτιο {room['number']} δεν είναι έτοιμο και η άφιξη "
                    f"του επισκέπτη πλησιάζει."
                ),
                recommended_actions=actions,
                evidence=evidence,
            ))
        return results

    def _guest_recovery_decisions(self) -> list[Decision]:
        results: list[Decision] = []

        for guest in self.guests.values():
            messages = guest.get("messages", [])
            sent = sentiment_score(messages)
            complaint_count = int(guest.get("complaint_count", 0))
            response_delay = float(guest.get("response_delay_minutes", 0))
            departure_h = hours_until(self.now, guest.get("departure"))

            if sent > -8 and complaint_count == 0 and response_delay < 15:
                continue

            negativity = abs(min(sent, 0))
            urgency = clamp(
                35
                + negativity * 0.55
                + min(response_delay, 60) * 0.65
                + (18 if departure_h < 24 else 0)
            )
            impact = clamp(
                35
                + complaint_count * 16
                + (15 if guest.get("loyalty_tier") in {"gold", "platinum"} else 0)
                + (10 if guest.get("vip") else 0)
            )
            confidence = clamp(70 + min(len(messages), 3) * 8 + complaint_count * 5)
            priority = weighted_priority(urgency, impact, confidence)

            max_comp = float(self.policies.get("max_auto_compensation_eur", 0))
            recommended_comp = min(
                float(self.policies.get("standard_recovery_credit_eur", 25)),
                max_comp if max_comp > 0 else 25,
            )

            actions = [
                {
                    "type": "draft_guest_message",
                    "label": "Δημιουργία απολογητικής απάντησης",
                    "payload": {
                        "guest_id": guest["id"],
                        "language": guest.get("language", "en"),
                        "tone": "empathetic",
                    },
                    "approval": ApprovalLevel.APPROVAL_REQUIRED.value,
                },
                {
                    "type": "create_frontdesk_task",
                    "label": "Άμεση επικοινωνία από reception",
                    "payload": {"guest_id": guest["id"], "priority": "urgent"},
                    "approval": ApprovalLevel.AUTO.value,
                },
            ]
            if recommended_comp > 0:
                actions.append({
                    "type": "offer_service_credit",
                    "label": f"Πρόταση πίστωσης €{recommended_comp:.0f}",
                    "payload": {
                        "guest_id": guest["id"],
                        "amount_eur": recommended_comp,
                    },
                    "approval": ApprovalLevel.APPROVAL_REQUIRED.value,
                })

            results.append(Decision(
                id=f"recovery-{guest['id']}",
                decision_type=DecisionType.GUEST_RECOVERY,
                title=f"Κίνδυνος δυσαρέσκειας: {guest['name']}",
                guest_id=guest["id"],
                room=guest.get("room"),
                priority=priority,
                urgency=round(urgency, 1),
                impact=round(impact, 1),
                confidence=round(confidence, 1),
                approval_level=ApprovalLevel.APPROVAL_REQUIRED,
                reason=(
                    "Αρνητικό μήνυμα, καθυστέρηση απόκρισης ή επαναλαμβανόμενο "
                    "παράπονο αυξάνει τον κίνδυνο αρνητικής εμπειρίας."
                ),
                recommended_actions=actions,
                evidence=[
                    f"Sentiment: {sent:.0f}",
                    f"Καθυστέρηση απάντησης: {response_delay:.0f} λεπτά",
                    f"Αριθμός παραπόνων: {complaint_count}",
                    f"Αναχώρηση σε {departure_h:.1f} ώρες",
                ],
            ))
        return results

    def _upsell_decisions(self) -> list[Decision]:
        results: list[Decision] = []

        for guest in self.guests.values():
            if guest.get("status") not in {"arriving", "in_house"}:
                continue
            already_offered = set(guest.get("offers_sent", []))
            preferences = set(guest.get("preferences", []))
            history = set(guest.get("purchase_history", []))
            stay_tags = set(guest.get("stay_tags", []))

            best: tuple[float, dict[str, Any], list[str]] | None = None

            for offer in self.offers:
                if not offer.get("available", False) or offer["id"] in already_offered:
                    continue

                fit = 15.0
                evidence = []
                tags = set(offer.get("tags", []))

                matched_preferences = tags & preferences
                matched_history = tags & history
                matched_stay = tags & stay_tags

                fit += 24 * min(len(matched_preferences), 2)
                fit += 20 * min(len(matched_history), 2)
                fit += 18 * min(len(matched_stay), 2)

                if matched_preferences:
                    evidence.append("Ταιριάζει με προτιμήσεις: " + ", ".join(sorted(matched_preferences)))
                if matched_history:
                    evidence.append("Υπάρχει σχετικό ιστορικό αγοράς")
                if matched_stay:
                    evidence.append("Ταιριάζει με τον σκοπό διαμονής")

                price = float(offer.get("price_eur", 0))
                budget = float(guest.get("estimated_upsell_budget_eur", 100))
                price_fit = clamp(100 - max(price - budget, 0) * 0.8)
                fit = clamp(0.8 * fit + 0.2 * price_fit)

                fatigue = len(already_offered) * 12
                probability = clamp(fit - fatigue)
                expected_value = round(price * probability / 100, 2)

                if best is None or expected_value > best[0]:
                    best = (expected_value, offer, evidence)

            if not best:
                continue

            expected_value, offer, evidence = best
            probability = 0 if float(offer["price_eur"]) == 0 else expected_value / float(offer["price_eur"]) * 100
            if probability < 45:
                continue

            arrival_h = hours_until(self.now, guest.get("arrival"))
            urgency = 70 if guest.get("status") == "arriving" and arrival_h < 8 else 50
            impact = clamp(35 + expected_value * 0.6)
            confidence = clamp(60 + len(evidence) * 10)
            priority = weighted_priority(urgency, impact, confidence)

            results.append(Decision(
                id=f"upsell-{guest['id']}-{offer['id']}",
                decision_type=DecisionType.UPSELL,
                title=f"Ευκαιρία upsell: {offer['name']}",
                guest_id=guest["id"],
                room=guest.get("room"),
                priority=priority,
                urgency=urgency,
                impact=round(impact, 1),
                confidence=round(confidence, 1),
                approval_level=ApprovalLevel.APPROVAL_REQUIRED,
                reason=(
                    f"Ο επισκέπτης έχει εκτιμώμενη πιθανότητα αγοράς "
                    f"{probability:.0f}% για την προσφορά «{offer['name']}»."
                ),
                recommended_actions=[{
                    "type": "draft_offer_message",
                    "label": "Δημιουργία προσωποποιημένης προσφοράς",
                    "payload": {
                        "guest_id": guest["id"],
                        "offer_id": offer["id"],
                        "price_eur": offer["price_eur"],
                        "language": guest.get("language", "en"),
                    },
                    "approval": ApprovalLevel.APPROVAL_REQUIRED.value,
                }],
                evidence=evidence or ["Κατάλληλη προσφορά βάσει γενικού προφίλ"],
                estimated_value_eur=expected_value,
            ))
        return results

    def _vip_decisions(self) -> list[Decision]:
        results: list[Decision] = []
        for guest in self.guests.values():
            if not guest.get("vip") or guest.get("status") != "arriving":
                continue
            arrival_h = hours_until(self.now, guest.get("arrival"))
            if arrival_h > 24:
                continue
            urgency = urgency_from_hours(arrival_h, 24)
            impact = 80
            confidence = 99
            results.append(Decision(
                id=f"vip-{guest['id']}",
                decision_type=DecisionType.VIP_ARRIVAL,
                title=f"Προετοιμασία VIP άφιξης: {guest['name']}",
                guest_id=guest["id"],
                room=guest.get("room"),
                priority=weighted_priority(urgency, impact, confidence),
                urgency=round(urgency, 1),
                impact=impact,
                confidence=confidence,
                approval_level=ApprovalLevel.AUTO,
                reason="VIP επισκέπτης αναμένεται μέσα στις επόμενες 24 ώρες.",
                recommended_actions=[
                    {
                        "type": "create_vip_checklist",
                        "label": "Δημιουργία VIP checklist",
                        "payload": {
                            "guest_id": guest["id"],
                            "preferences": guest.get("preferences", []),
                        },
                        "approval": ApprovalLevel.AUTO.value,
                    }
                ],
                evidence=[
                    f"Άφιξη σε {arrival_h:.1f} ώρες",
                    "VIP flag ενεργό",
                ],
            ))
        return results

    def _maintenance_decisions(self) -> list[Decision]:
        results: list[Decision] = []
        for room in self.rooms.values():
            issue = room.get("maintenance_issue")
            if not issue:
                continue

            severity = {"low": 35, "medium": 60, "high": 85, "critical": 100}.get(
                issue.get("severity", "medium"), 60
            )
            occupied = room.get("occupied", False)
            urgency = clamp(severity + (10 if occupied else 0))
            impact = clamp(severity + (15 if occupied else 0))
            confidence = 95

            approval = (
                ApprovalLevel.HUMAN_ONLY
                if issue.get("severity") == "critical"
                else ApprovalLevel.AUTO
            )

            results.append(Decision(
                id=f"maintenance-{room['number']}",
                decision_type=DecisionType.MAINTENANCE,
                title=f"Maintenance στο δωμάτιο {room['number']}",
                guest_id=room.get("current_guest_id"),
                room=room["number"],
                priority=weighted_priority(urgency, impact, confidence),
                urgency=round(urgency, 1),
                impact=round(impact, 1),
                confidence=confidence,
                approval_level=approval,
                reason=issue.get("description", "Εντοπίστηκε τεχνικό πρόβλημα."),
                recommended_actions=[{
                    "type": "create_maintenance_task",
                    "label": "Δημιουργία τεχνικού task",
                    "payload": {
                        "room": room["number"],
                        "severity": issue.get("severity", "medium"),
                        "description": issue.get("description", ""),
                    },
                    "approval": approval.value,
                }],
                evidence=[
                    f"Σοβαρότητα: {issue.get('severity', 'medium')}",
                    f"Κατειλημμένο δωμάτιο: {'ναι' if occupied else 'όχι'}",
                ],
            ))
        return results

    def briefing(self, limit: int = 5) -> dict[str, Any]:
        decisions = self.analyze()
        arrivals = sum(1 for g in self.guests.values() if g.get("status") == "arriving")
        departures = sum(
            1 for g in self.guests.values()
            if 0 <= hours_until(self.now, g.get("departure")) <= 24
        )
        vip_arrivals = sum(
            1 for g in self.guests.values()
            if g.get("status") == "arriving" and g.get("vip")
        )
        estimated_value = round(sum(d.estimated_value_eur for d in decisions), 2)

        return {
            "generated_at": self.now.isoformat(),
            "hotel": self.state.get("hotel", {}),
            "summary": {
                "arrivals": arrivals,
                "departures_next_24h": departures,
                "vip_arrivals": vip_arrivals,
                "open_decisions": len(decisions),
                "estimated_upsell_value_eur": estimated_value,
            },
            "top_priorities": [d.to_dict() for d in decisions[:limit]],
        }

    def answer(self, question: str) -> dict[str, Any]:
        """
        Lightweight demo query router.
        In production, an LLM should map natural language to one of these
        intents, while this engine remains the source of truth.
        """
        q = question.lower()
        decisions = self.analyze()

        if any(k in q for k in ["vip", "σημαντικ", "important guest"]):
            selected = [d for d in decisions if d.decision_type == DecisionType.VIP_ARRIVAL]
            intent = "vip_arrivals"
        elif any(k in q for k in ["δωμάτι", "room", "καθαρισ", "housekeeping"]):
            selected = [d for d in decisions if d.decision_type == DecisionType.ROOM_READINESS]
            intent = "room_readiness"
        elif any(k in q for k in ["παράπον", "δυσαρεστ", "complaint", "unhappy", "προσοχή"]):
            selected = [d for d in decisions if d.decision_type == DecisionType.GUEST_RECOVERY]
            intent = "guest_recovery"
        elif any(k in q for k in ["upsell", "spa", "προσφορ", "έσοδ"]):
            selected = [d for d in decisions if d.decision_type == DecisionType.UPSELL]
            intent = "upsell"
        elif any(k in q for k in ["maintenance", "βλάβ", "τεχνικ"]):
            selected = [d for d in decisions if d.decision_type == DecisionType.MAINTENANCE]
            intent = "maintenance"
        else:
            selected = decisions[:5]
            intent = "top_priorities"

        return {
            "intent": intent,
            "answer": (
                f"Βρήκα {len(selected)} σχετικές περιπτώσεις. "
                f"Η υψηλότερη προτεραιότητα είναι: "
                f"{selected[0].title if selected else 'καμία'}."
            ),
            "items": [d.to_dict() for d in selected[:10]],
        }


def load_state(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Hotel AI Brain demo")
    parser.add_argument("data", nargs="?", default="demo_data.json")
    parser.add_argument("--question", help="Natural-language demo question")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    brain = HotelBrain(load_state(args.data))
    output = brain.answer(args.question) if args.question else brain.briefing(args.limit)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
