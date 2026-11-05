const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface SessionData {
  session_id: string;
  token: string;
  status: string;
}

export interface DocumentSummary {
  document_id: string;
  original_filename: string;
  state: string;
  created_at: string;
  page_count: number;
}

export interface ProofRef {
  page_number?: number;
  block_id: string;
  bbox?: number[];
  text?: string;
}

export interface ActionCardData {
  card_id: string;
  title: string;
  what_says: string;
  what_means: string;
  what_action: string;
  uncertainty?: string | null;
  proof_refs: ProofRef[];
  status: string;
  approved_spoken_output?: string;
}

export interface TextBlockData {
  block_id: string;
  page_index: number;
  text_original: string;
  bbox?: number[];
  confidence: number;
}

export interface AnswerResponse {
  answer_status: string;
  summary_text: string;
  approved_spoken_output?: string;
  claims: Array<{
    claim_id: string;
    claim_text: string;
    status: string;
    evidence: any[];
    reason_code?: string;
  }>;
  uncertainties?: string[];
  action_advice?: string;
  disclaimer?: string;
}

class ApiClient {
  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {};
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("ns_session_token");
      if (token) {
        headers["X-Session-Token"] = token;
      }
    }
    return headers;
  }

  async initSession(): Promise<SessionData> {
    let storedToken = null;
    if (typeof window !== "undefined") {
      storedToken = localStorage.getItem("ns_session_token");
    }
    const url = storedToken
      ? `${API_BASE}/auth/session?token=${encodeURIComponent(storedToken)}`
      : `${API_BASE}/auth/session`;
      
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("Failed to initialize session");
    const data: SessionData = await res.json();
    if (typeof window !== "undefined") {
      localStorage.setItem("ns_session_token", data.token);
    }
    return data;
  }

  async uploadDocument(file: File): Promise<{ document_id: string; state: string; page_count: number }> {
    await this.ensureSession();
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/documents`, {
      method: "POST",
      headers: this.getHeaders(),
      body: formData,
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData?.detail?.message || "Document upload failed");
    }
    return res.json();
  }

  async listDocuments(): Promise<DocumentSummary[]> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to list documents");
    return res.json();
  }

  async getDocument(documentId: string): Promise<any> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Document not found");
    return res.json();
  }

  async getDocumentStatus(documentId: string): Promise<{ document_id: string; state: string; message: string }> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}/status`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document status");
    return res.json();
  }

  async getActionCards(documentId: string): Promise<{ document_id: string; document_state: string; cards: ActionCardData[] }> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}/action-cards`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch action cards");
    return res.json();
  }

  async getDocumentPages(documentId: string): Promise<{ document_id: string; blocks: TextBlockData[] }> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}/pages`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch document pages");
    return res.json();
  }

  async askQuestion(
    documentId: string,
    questionText: string,
    language: string = "te-IN",
    consentForCloudTranslation: boolean = false
  ): Promise<AnswerResponse> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}/questions`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question_text: questionText,
        response_language: language,
        consent_for_cloud_translation: consentForCloudTranslation,
      }),
    });
    if (!res.ok) throw new Error("Failed to answer question");
    return res.json();
  }

  async submitVoiceTurn(documentId: string, audioBlob: Blob, language: string = "te-IN"): Promise<any> {
    await this.ensureSession();
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "question.wav");
    formData.append("language_code", language);

    const res = await fetch(`${API_BASE}/documents/${documentId}/voice-turns`, {
      method: "POST",
      headers: this.getHeaders(),
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to process speech input");
    return res.json();
  }

  async getConsentStatus(): Promise<{ actor_id: string; consents: Record<string, any> }> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/auth/consent`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch consent status");
    return res.json();
  }

  async updateConsent(consents: Record<string, boolean>): Promise<any> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/auth/consent`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ consents }),
    });
    if (!res.ok) throw new Error("Failed to update consent preferences");
    return res.json();
  }

  async synthesizeSpeech(text: string, language: string = "te-IN", speed: number = 1.0): Promise<string> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/speech/synthesize`, {
      method: "POST",
      headers: {
        ...this.getHeaders(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        language,
        speed,
      }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.detail?.message || "Speech synthesis failed");
    }
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  }

  async deleteDocument(documentId: string): Promise<any> {
    await this.ensureSession();
    const res = await fetch(`${API_BASE}/documents/${documentId}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete document");
    return res.json();
  }

  private async ensureSession(): Promise<void> {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("ns_session_token");
      if (!token) {
        await this.initSession();
      }
    }
  }
}

export const api = new ApiClient();

