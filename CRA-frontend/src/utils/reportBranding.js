import PizZip from 'pizzip';

/**
 * Takes an existing DOCX blob and prepends branding to it.
 * Injects logo, company name, and address directly into the DOCX XML.
 */

export async function injectBrandingIntoDocx(docxBlob, { logoFile, companyName, companyAddress }) {
  // Read the blob as ArrayBuffer
  const arrayBuffer = await docxBlob.arrayBuffer();
  const zip = new PizZip(arrayBuffer);

  // Read document.xml
  const documentXml = zip.file('word/document.xml').asText();
  const relsXml = zip.file('word/_rels/document.xml.rels').asText();
  const contentTypesXml = zip.file('[Content_Types].xml').asText();

  let newDocumentXml = documentXml;
  let newRelsXml = relsXml;
  let newContentTypesXml = contentTypesXml;

  // Build the branding XML to insert at start of <w:body>
  let brandingXml = '';

  // Add logo if provided
  if (logoFile) {
    const logoBuffer = await logoFile.arrayBuffer();
    const logoBytes = new Uint8Array(logoBuffer);
    const ext = logoFile.name.split('.').pop().toLowerCase();
    const mediaType = ext === 'png' ? 'image/png' : 'image/jpeg';

    // Add image to zip
    zip.file(`word/media/logo_brand.${ext}`, logoBytes);

    // Add relationship
    const rId = 'rIdLogo1';
    newRelsXml = newRelsXml.replace(
      '</Relationships>',
      `<Relationship Id="${rId}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo_brand.${ext}"/></Relationships>`
    );

    // Add content type if png
    if (ext === 'png' && !newContentTypesXml.includes('image/png')) {
      newContentTypesXml = newContentTypesXml.replace(
        '</Types>',
        `<Default Extension="png" ContentType="image/png"/></Types>`
      );
    }

    // Logo paragraph XML (2 inches wide = 1828800 EMUs)
    brandingXml += `
      <w:p>
        <w:pPr><w:jc w:val="center"/></w:pPr>
        <w:r>
          <w:drawing>
            <wp:inline xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
                       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                       xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
              <wp:extent cx="1828800" cy="1085184"/>
              <wp:docPr id="99" name="BrandLogo"/>
              <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>
              <a:graphic>
                <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:pic>
                    <pic:nvPicPr>
                      <pic:cNvPicPr/>
                      <pic:cNvPicPr/>
                    </pic:nvPicPr>
                    <pic:blipFill>
                      <a:blip r:embed="${rId}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>
                      <a:stretch><a:fillRect/></a:stretch>
                    </pic:blipFill>
                    <pic:spPr>
                      <a:xfrm><a:off x="0" y="0"/><a:ext cx="1828800" cy="1085184"/></a:xfrm>
                      <a:prstGeom prst="rect"/>
                    </pic:spPr>
                  </pic:pic>
                </a:graphicData>
              </a:graphic>
            </wp:inline>
          </w:drawing>
        </w:r>
      </w:p>`;
  }

  // Company name paragraph
  if (companyName && companyName.trim()) {
    brandingXml += `
      <w:p>
        <w:pPr><w:jc w:val="center"/></w:pPr>
        <w:r>
          <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
          <w:t>${escapeXml(companyName.trim())}</w:t>
        </w:r>
      </w:p>`;
  }

  // Company address paragraph
  if (companyAddress && companyAddress.trim()) {
    brandingXml += `
      <w:p>
        <w:pPr><w:jc w:val="center"/></w:pPr>
        <w:r>
          <w:rPr><w:sz w:val="22"/></w:rPr>
          <w:t>${escapeXml(companyAddress.trim())}</w:t>
        </w:r>
      </w:p>`;
  }

  // Inject branding right after <w:body>
  newDocumentXml = newDocumentXml.replace('<w:body>', '<w:body>' + brandingXml);

  // Save back to zip
  zip.file('word/document.xml', newDocumentXml);
  zip.file('word/_rels/document.xml.rels', newRelsXml);
  zip.file('[Content_Types].xml', newContentTypesXml);

  // Generate new blob
  const output = zip.generate({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
  return output;
}

function escapeXml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}
