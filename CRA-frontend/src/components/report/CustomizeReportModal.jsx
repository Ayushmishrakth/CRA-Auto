import React, { useRef, useState } from "react";
import { tokenStorage } from "../../utils/tokenStorage";

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8000/api/v1";

function safeFileName(value) {
  return String(value || "Report").replace(/\s+/g, "_").replace(/[^a-zA-Z0-9_-]/g, "");
}

export default function CustomizeReportModal({ assessmentId, tenantName, onClose }) {
  const [logoFile, setLogoFile] = useState(null);
  const [logoPreview, setPreview] = useState(null);
  const [companyName, setName] = useState("");
  const [address, setAddress] = useState("");
  const [format, setFormat] = useState("docx");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef();

  const onFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setLogoFile(file);
    const reader = new FileReader();
    reader.onload = (loadEvent) => setPreview(loadEvent.target.result);
    reader.readAsDataURL(file);
  };

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const formData = new FormData();
      if (logoFile) formData.append("logo_file", logoFile);
      if (companyName.trim()) formData.append("company_name", companyName.trim());
      if (address.trim()) formData.append("company_address", address.trim());

      const token =
        tokenStorage.getAccessToken() ||
        localStorage.getItem("token") ||
        localStorage.getItem("access_token") ||
        sessionStorage.getItem("token") ||
        "";

      const response = await fetch(
        `${apiBaseUrl}/assessments/${assessmentId}/generate-report?report_type=${format}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        }
      );

      if (!response.ok) throw new Error((await response.text()) || `Error ${response.status}`);

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `CRA_Report_${safeFileName(tenantName || assessmentId)}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",
                 display:"flex",alignItems:"center",justifyContent:"center",zIndex:9999}}>
      <div style={{background:"#fff",borderRadius:12,padding:32,width:480,
                   maxWidth:"90vw",maxHeight:"90vh",overflowY:"auto",
                   boxShadow:"0 20px 60px rgba(0,0,0,0.3)"}}>
        <h2 style={{margin:"0 0 24px",fontSize:20,fontWeight:700}}>Customize Report</h2>

        <div style={{marginBottom:20}}>
          <label style={{display:"block",fontWeight:600,marginBottom:8}}>Company Logo</label>
          <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,.svg"
                 onChange={onFile} style={{display:"none"}} />
          {logoPreview
            ? <div style={{display:"flex",alignItems:"center",gap:12,padding:12,
                           border:"2px solid #e5e7eb",borderRadius:8}}>
                <img src={logoPreview} alt="logo" style={{height:50,maxWidth:160,objectFit:"contain"}} />
                <button onClick={() => inputRef.current.click()}
                        style={{background:"none",border:"1px solid #2563eb",color:"#2563eb",
                                padding:"4px 12px",borderRadius:6,cursor:"pointer"}}>Change</button>
              </div>
            : <button onClick={() => inputRef.current.click()}
                      style={{background:"#2563eb",color:"#fff",padding:"10px 20px",
                              borderRadius:8,border:"none",cursor:"pointer",
                              fontSize:14,fontWeight:600,width:"100%"}}>
                Upload Logo
              </button>
          }
          <small style={{color:"#888"}}>PNG, JPG, or SVG (max 5MB)</small>
        </div>

        <div style={{marginBottom:20}}>
          <label style={{display:"block",fontWeight:600,marginBottom:8}}>Company Name</label>
          <input type="text" value={companyName} onChange={(event) => setName(event.target.value)}
                 placeholder="e.g., Acme Corporation"
                 style={{width:"100%",padding:"10px 12px",border:"1px solid #d1d5db",
                         borderRadius:8,fontSize:14,boxSizing:"border-box"}} />
        </div>

        <div style={{marginBottom:20}}>
          <label style={{display:"block",fontWeight:600,marginBottom:8}}>Company Address</label>
          <textarea value={address} onChange={(event) => setAddress(event.target.value)}
                    placeholder="e.g., 123 Business St, City"
                    style={{width:"100%",padding:"10px 12px",border:"1px solid #d1d5db",
                            borderRadius:8,fontSize:14,minHeight:80,
                            boxSizing:"border-box",resize:"vertical"}} />
        </div>

        <div style={{marginBottom:20}}>
          <label style={{display:"block",fontWeight:600,marginBottom:8}}>Report Format</label>
          {[["docx","Word Document (.docx)"],["pdf","PDF Document (.pdf)"]].map(([value,label]) => (
            <label key={value} style={{display:"flex",alignItems:"center",padding:"12px 16px",
                                       border:"1px solid #e5e7eb",borderRadius:8,
                                       marginBottom:8,cursor:"pointer"}}>
              <input type="radio" name="fmt" value={value}
                     checked={format===value} onChange={() => setFormat(value)} />
              <span style={{marginLeft:8}}>{label}</span>
              {value==="docx" && <span style={{marginLeft:"auto",background:"#f0f9ff",
                                               color:"#0369a1",padding:"2px 8px",
                                               borderRadius:12,fontSize:11}}>Recommended</span>}
            </label>
          ))}
        </div>

        {error && <div style={{background:"#fef2f2",color:"#dc2626",padding:12,
                               borderRadius:8,marginBottom:16,fontSize:13}}>{error}</div>}

        <div style={{display:"flex",gap:12,justifyContent:"flex-end"}}>
          <button onClick={onClose} disabled={loading}
                  style={{padding:"10px 24px",border:"1px solid #d1d5db",
                          borderRadius:8,background:"#fff",cursor:"pointer"}}>Cancel</button>
          <button onClick={generate} disabled={loading}
                  style={{padding:"10px 24px",background:"#2563eb",color:"#fff",
                          border:"none",borderRadius:8,cursor:"pointer",
                          fontWeight:600,opacity:loading?0.7:1}}>
            {loading ? "Generating..." : "Apply & Generate"}
          </button>
        </div>
      </div>
    </div>
  );
}
