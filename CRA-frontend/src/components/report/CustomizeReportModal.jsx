import { useState, useRef } from "react";
import { Upload, X, AlertCircle } from "lucide-react";
import Button from "../ui/Button";
import { useToast } from "../../context/ToastContext";
import { injectBrandingIntoDocx } from "../../utils/reportBranding";
import { saveAs } from "file-saver";
import axios from "axios";

const MAX_LOGO_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_TYPES = ["image/png", "image/jpeg", "image/svg+xml"];

export default function CustomizeReportModal({ assessmentId, onClose, onGenerate, isLoading = false }) {
  const toast = useToast();
  const fileInputRef = useRef(null);

  const [formState, setFormState] = useState({
    logoFile: null,
    logoPreview: null,
    companyName: "",
    companyAddress: "",
    format: "pdf",
  });

  const [validation, setValidation] = useState({
    logoSize: null,
    logoType: null,
  });

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const newValidation = { logoSize: null, logoType: null };

    if (file.size > MAX_LOGO_SIZE) {
      newValidation.logoSize = "Logo must be smaller than 5MB";
      toast.error("Logo file too large (max 5MB)");
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      newValidation.logoType = "Only PNG, JPG, and SVG files are allowed";
      toast.error("Invalid logo format. Allowed: PNG, JPG, SVG");
    }

    setValidation(newValidation);

    if (!newValidation.logoSize && !newValidation.logoType) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setFormState((prev) => ({
          ...prev,
          logoFile: file,
          logoPreview: evt.target.result,
        }));
      };
      reader.readAsDataURL(file);
    } else {
      e.target.value = "";
    }
  };

  const handleRemoveLogo = () => {
    setFormState((prev) => ({
      ...prev,
      logoFile: null,
      logoPreview: null,
    }));
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormState((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleGenerate = async () => {
    try {
      const companyName = formState.companyName.trim();
      const companyAddress = formState.companyAddress.trim();
      const logoFile = formState.logoFile;

      // Download plain DOCX from backend
      const response = await axios.get(
        `/api/v1/assessments/${assessmentId}/report/download?report_type=docx`,
        { responseType: 'blob' }
      );

      // Inject branding in browser
      const brandedBlob = await injectBrandingIntoDocx(response.data, {
        logoFile: logoFile,
        companyName: companyName,
        companyAddress: companyAddress,
      });

      // Save to user's computer
      const timestamp = new Date().toISOString().slice(0, 10);
      const filename = `CRA_Report_${companyName || 'Report'}_${timestamp}.docx`;
      saveAs(brandedBlob, filename);

      toast.success("Report generated and downloaded successfully!");
      onClose();
    } catch (error) {
      console.error('Report generation failed:', error);
      toast.error(error.message || "Failed to generate report");
    }
  };

  const hasValidationErrors = validation.logoSize || validation.logoType;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900">Customize Report</h2>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {/* Logo Upload */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              Company Logo
            </label>
            <div className="space-y-3">
              {formState.logoPreview ? (
                <div className="relative bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-4 flex items-center justify-center">
                  <img
                    src={formState.logoPreview}
                    alt="Logo preview"
                    className="max-h-24 max-w-full object-contain"
                  />
                  <button
                    type="button"
                    onClick={handleRemoveLogo}
                    disabled={isLoading}
                    className="absolute top-2 right-2 bg-red-100 text-red-600 p-1 rounded-full hover:bg-red-200 disabled:opacity-50"
                    aria-label="Remove logo"
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="w-full border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Upload size={24} className="mx-auto mb-2 text-gray-400" />
                  <p className="text-sm font-medium text-gray-700">Click to upload</p>
                  <p className="text-xs text-gray-500 mt-1">PNG, JPG or SVG • Max 5MB</p>
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/svg+xml"
                onChange={handleLogoChange}
                disabled={isLoading}
                className="hidden"
                aria-label="Logo file input"
              />
              {hasValidationErrors && (
                <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-3 rounded">
                  <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                  <div>
                    {validation.logoSize && <p>{validation.logoSize}</p>}
                    {validation.logoType && <p>{validation.logoType}</p>}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Company Name */}
          <div>
            <label htmlFor="companyName" className="block text-sm font-semibold text-gray-900 mb-2">
              Company Name
            </label>
            <input
              id="companyName"
              type="text"
              name="companyName"
              value={formState.companyName}
              onChange={handleInputChange}
              disabled={isLoading}
              placeholder="Enter your company name"
              maxLength={200}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">
              {formState.companyName.length}/200
            </p>
          </div>

          {/* Company Address */}
          <div>
            <label htmlFor="companyAddress" className="block text-sm font-semibold text-gray-900 mb-2">
              Company Address
            </label>
            <textarea
              id="companyAddress"
              name="companyAddress"
              value={formState.companyAddress}
              onChange={handleInputChange}
              disabled={isLoading}
              placeholder="Enter your company address"
              maxLength={500}
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="text-xs text-gray-500 mt-1">
              {formState.companyAddress.length}/500
            </p>
          </div>

          {/* Report Format */}
          <div>
            <label className="block text-sm font-semibold text-gray-900 mb-3">
              Report Format
            </label>
            <div className="space-y-2">
              {[
                { value: "pdf", label: "PDF (.pdf)" },
                { value: "docx", label: "Word (.docx)" },
                { value: "both", label: "Both PDF & Word (.zip)" },
              ].map((option) => (
                <label
                  key={option.value}
                  className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <input
                    type="radio"
                    name="format"
                    value={option.value}
                    checked={formState.format === option.value}
                    onChange={handleInputChange}
                    disabled={isLoading}
                    className="w-4 h-4 text-blue-600 cursor-pointer disabled:cursor-not-allowed"
                  />
                  <span className="text-sm font-medium text-gray-700">{option.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-4 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Cancel
          </button>
          <Button
            variant="primary"
            onClick={handleGenerate}
            disabled={isLoading}
          >
            {isLoading ? "Generating..." : "Generate & Download"}
          </Button>
        </div>
      </div>
    </div>
  );
}
