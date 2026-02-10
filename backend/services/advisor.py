"""
Advisor Portal Service

Handles all Firestore operations for advisor assignments, notes, and alerts.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.config import get_firestore_client, initialize_firebase


class AdvisorService:
    """Service for managing advisor data in Firebase Firestore."""

    ASSIGNMENTS_COLLECTION = "advisor_assignments"
    NOTES_COLLECTION = "advisor_notes"
    STUDENTS_COLLECTION = "students"

    def __init__(self):
        self.db = get_firestore_client()

    # --- Advisee Assignment Operations ---

    def get_advisees(self, advisor_id: str) -> List[Dict[str, Any]]:
        """Get all students assigned to an advisor."""
        query = self.db.collection(self.ASSIGNMENTS_COLLECTION).where(
            "advisorId", "==", advisor_id
        )

        advisees = []
        for doc in query.stream():
            assignment = doc.to_dict()
            assignment["id"] = doc.id

            # Fetch student details
            student_id = assignment.get("studentId")
            if student_id:
                student_doc = self.db.collection(self.STUDENTS_COLLECTION).document(student_id).get()
                if student_doc.exists:
                    student_data = student_doc.to_dict()
                    student_data["id"] = student_doc.id
                    assignment["student"] = student_data

            advisees.append(assignment)

        return advisees

    def get_advisee(self, advisor_id: str, student_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific advisee's details."""
        # Verify assignment exists
        query = self.db.collection(self.ASSIGNMENTS_COLLECTION)\
            .where("advisorId", "==", advisor_id)\
            .where("studentId", "==", student_id)\
            .limit(1)

        assignments = list(query.stream())
        if not assignments:
            return None

        # Get student details
        student_doc = self.db.collection(self.STUDENTS_COLLECTION).document(student_id).get()
        if not student_doc.exists:
            return None

        student_data = student_doc.to_dict()
        student_data["id"] = student_doc.id

        # Include assignment info
        assignment = assignments[0].to_dict()
        student_data["assignmentId"] = assignments[0].id
        student_data["assignedDate"] = assignment.get("assignedDate")

        return student_data

    def assign_advisee(self, advisor_id: str, student_id: str) -> Dict[str, Any]:
        """Assign a student to an advisor."""
        # Check if already assigned
        query = self.db.collection(self.ASSIGNMENTS_COLLECTION)\
            .where("advisorId", "==", advisor_id)\
            .where("studentId", "==", student_id)\
            .limit(1)

        existing = list(query.stream())
        if existing:
            data = existing[0].to_dict()
            data["id"] = existing[0].id
            return data

        assignment_data = {
            "advisorId": advisor_id,
            "studentId": student_id,
            "assignedDate": datetime.utcnow().isoformat()
        }

        doc_ref = self.db.collection(self.ASSIGNMENTS_COLLECTION).document()
        doc_ref.set(assignment_data)
        assignment_data["id"] = doc_ref.id

        return assignment_data

    def remove_advisee(self, advisor_id: str, student_id: str) -> bool:
        """Remove a student from an advisor's list."""
        query = self.db.collection(self.ASSIGNMENTS_COLLECTION)\
            .where("advisorId", "==", advisor_id)\
            .where("studentId", "==", student_id)\
            .limit(1)

        assignments = list(query.stream())
        if not assignments:
            return False

        assignments[0].reference.delete()
        return True

    # --- Note Operations ---

    def get_notes(self, advisor_id: str, student_id: str) -> List[Dict[str, Any]]:
        """Get all notes for a student from an advisor."""
        query = self.db.collection(self.NOTES_COLLECTION)\
            .where("advisorId", "==", advisor_id)\
            .where("studentId", "==", student_id)

        notes = []
        for doc in query.stream():
            note = doc.to_dict()
            note["id"] = doc.id
            notes.append(note)

        # Sort by createdAt descending
        notes.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
        return notes

    def create_note(
        self, advisor_id: str, student_id: str, note: str, visibility: str = "private"
    ) -> Dict[str, Any]:
        """Create a new note for a student."""
        note_data = {
            "advisorId": advisor_id,
            "studentId": student_id,
            "note": note,
            "visibility": visibility,
            "createdAt": datetime.utcnow().isoformat(),
            "updatedAt": datetime.utcnow().isoformat()
        }

        doc_ref = self.db.collection(self.NOTES_COLLECTION).document()
        doc_ref.set(note_data)
        note_data["id"] = doc_ref.id

        return note_data

    def update_note(
        self, advisor_id: str, note_id: str, note: Optional[str] = None, visibility: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing note."""
        doc_ref = self.db.collection(self.NOTES_COLLECTION).document(note_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        existing = doc.to_dict()
        # Verify ownership
        if existing.get("advisorId") != advisor_id:
            return None

        update_data = {"updatedAt": datetime.utcnow().isoformat()}
        if note is not None:
            update_data["note"] = note
        if visibility is not None:
            update_data["visibility"] = visibility

        doc_ref.update(update_data)

        updated_doc = doc_ref.get()
        result = updated_doc.to_dict()
        result["id"] = note_id
        return result

    def delete_note(self, advisor_id: str, note_id: str) -> bool:
        """Delete a note."""
        doc_ref = self.db.collection(self.NOTES_COLLECTION).document(note_id)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        existing = doc.to_dict()
        # Verify ownership
        if existing.get("advisorId") != advisor_id:
            return False

        doc_ref.delete()
        return True

    # --- Alert Operations ---

    def get_alerts(self, advisor_id: str) -> List[Dict[str, Any]]:
        """Get alerts for an advisor's advisees."""
        # Get all advisees
        advisees = self.get_advisees(advisor_id)
        student_ids = [a.get("studentId") for a in advisees if a.get("studentId")]

        alerts = []

        for student_id in student_ids:
            student_doc = self.db.collection(self.STUDENTS_COLLECTION).document(student_id).get()
            if not student_doc.exists:
                continue

            student = student_doc.to_dict()
            student_name = student.get("name", "Unknown")

            # Check for holds
            holds = student.get("holds", [])
            for hold in holds:
                alerts.append({
                    "type": "hold",
                    "severity": "high",
                    "studentId": student_id,
                    "studentName": student_name,
                    "message": f"Student has a hold: {hold}",
                    "createdAt": datetime.utcnow().isoformat()
                })

            # Check for low GPA
            gpa = student.get("gpa")
            if gpa is not None and gpa < 2.0:
                alerts.append({
                    "type": "gpa",
                    "severity": "high",
                    "studentId": student_id,
                    "studentName": student_name,
                    "message": f"Student GPA is below 2.0: {gpa}",
                    "createdAt": datetime.utcnow().isoformat()
                })
            elif gpa is not None and gpa < 2.5:
                alerts.append({
                    "type": "gpa",
                    "severity": "medium",
                    "studentId": student_id,
                    "studentName": student_name,
                    "message": f"Student GPA is below 2.5: {gpa}",
                    "createdAt": datetime.utcnow().isoformat()
                })

            # Check for undeclared major (if past typical declaration point)
            class_year = student.get("classYear")
            declared = student.get("declared", False)
            if class_year and not declared:
                current_year = datetime.utcnow().year
                years_until_grad = class_year - current_year
                if years_until_grad <= 2:  # Junior or Senior
                    alerts.append({
                        "type": "declaration",
                        "severity": "medium",
                        "studentId": student_id,
                        "studentName": student_name,
                        "message": "Student has not declared a major",
                        "createdAt": datetime.utcnow().isoformat()
                    })

        # Sort by severity (high first)
        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

        return alerts


_advisor_service: Optional[AdvisorService] = None


def get_advisor_service() -> AdvisorService:
    """Get singleton instance of AdvisorService."""
    global _advisor_service
    if _advisor_service is None:
        initialize_firebase()
        _advisor_service = AdvisorService()
    return _advisor_service
