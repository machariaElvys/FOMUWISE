from app import db


class Document(db.Model):
    __tablename__ = "documents"

    document_id = db.Column(db.String(36), primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False, default="application/pdf")
    file_size_bytes = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    analysis_json = db.Column(db.JSON, nullable=False)
    access_token_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    pages = db.relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )


class DocumentPage(db.Model):
    __tablename__ = "document_pages"
    __table_args__ = (
        db.UniqueConstraint("document_id", "page_number", name="uq_document_page_number"),
    )

    page_id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.String(36),
        db.ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number = db.Column(db.Integer, nullable=False)
    page_text = db.Column(db.Text, nullable=False)
    document = db.relationship("Document", back_populates="pages")
