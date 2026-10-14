import { useRef, useState } from "react";
import { FileText, Upload } from "lucide-react";

function EmailUploader({ onEmailLoaded }) {
  const fileInputRef = useRef(null);

  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const processFile = async (file) => {
    setError("");

    if (!file) {
      return;
    }

    const extension = file.name.split(".").pop()?.toLowerCase();

    if (extension !== "eml") {
      setError("Please upload an .eml email file.");
      return;
    }

    try {
      const rawEmail = await file.text();

      console.log("Loaded EML:", file.name);

      const email = parseEmail(rawEmail);

      console.log("Parsed email:", email);

      if (!email.subject && !email.body) {
        throw new Error("No email content found.");
      }

      onEmailLoaded({
        from: email.from || "Unknown Sender",
        to: email.to || "",
        subject: email.subject || "No Subject",
        date: email.date || "",
        body: email.body || "No email body found.",
      });
    } catch (err) {
      console.error("Email parsing failed:", err);

      setError(
        "Unable to read this email. Check the browser console for details.",
      );
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    await processFile(file);

    event.target.value = "";
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    setDragging(false);
  };

  const handleDrop = async (event) => {
    event.preventDefault();
    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    if (!file) {
      return;
    }

    await processFile(file);
  };

  return (
    <div className="upload-section">
      <div
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-icon">
          <Upload size={25} />
        </div>

        <h2>Upload Support Email</h2>

        <p>Drop an Outlook .eml email here or select one from your computer.</p>

        <button
          type="button"
          className="browse-button"
          onClick={openFilePicker}
        >
          <FileText size={15} />
          Choose Email
        </button>

        <span className="file-support">Supports .eml files</span>

        <input
          ref={fileInputRef}
          type="file"
          accept=".eml,message/rfc822"
          onChange={handleFileChange}
          style={{
            display: "none",
          }}
        />
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

function parseEmail(rawEmail) {
  const normalised = rawEmail.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  const headers = extractHeaders(normalised);
  const body = extractEmailBody(normalised);

  return {
    ...headers,
    body,
  };
}

function extractHeaders(rawEmail) {
  const getHeader = (name) => {
    const match = rawEmail.match(
      new RegExp(`^${name}:\\s*(.+(?:\\n[ \\t].+)*)`, "im"),
    );

    if (!match) {
      return "";
    }

    const value = match[1].replace(/\n[ \t]+/g, " ").trim();

    return decodeMimeWords(value);
  };

  return {
    from: extractEmailAddress(getHeader("From")),

    subject: getHeader("Subject") || "No Subject",
    date: getHeader("Date"),
  };
}
function extractEmailAddress(value) {
  if (!value) {
    return "";
  }

  const match = value.match(/<([^<>]+)>/);

  return match ? match[1].trim() : value.trim();
}
function extractEmailBody(rawEmail) {
  const plainBody = extractPlainTextPart(rawEmail);

  if (plainBody) {
    return cleanBody(plainBody);
  }

  const htmlBody = extractHtmlPart(rawEmail);

  if (htmlBody) {
    return cleanBody(htmlToText(htmlBody));
  }

  const separatorIndex = rawEmail.indexOf("\n\n");

  if (separatorIndex === -1) {
    return "";
  }

  const body = rawEmail.slice(separatorIndex + 2);

  return cleanBody(decodeQuotedPrintable(body));
}

function extractPlainTextPart(rawEmail) {
  const plainTypeMatch = /Content-Type:\s*text\/plain[^\n]*\n/i.exec(rawEmail);

  if (!plainTypeMatch) {
    return "";
  }

  const partStart = plainTypeMatch.index;
  const afterType = rawEmail.slice(partStart);
  const headerEnd = afterType.indexOf("\n\n");

  if (headerEnd === -1) {
    return "";
  }

  let body = afterType.slice(headerEnd + 2);

  const boundaryMatch = body.match(/\n--[^\n]+/);

  if (boundaryMatch) {
    body = body.slice(0, boundaryMatch.index);
  }

  const headers = afterType.slice(0, headerEnd);

  if (/Content-Transfer-Encoding:\s*base64/i.test(headers)) {
    body = decodeBase64(body);
  }

  if (/Content-Transfer-Encoding:\s*quoted-printable/i.test(headers)) {
    body = decodeQuotedPrintable(body);
  }

  return body;
}

function extractHtmlPart(rawEmail) {
  const htmlTypeMatch = /Content-Type:\s*text\/html[^\n]*\n/i.exec(rawEmail);

  if (!htmlTypeMatch) {
    return "";
  }

  const partStart = htmlTypeMatch.index;
  const afterType = rawEmail.slice(partStart);
  const headerEnd = afterType.indexOf("\n\n");

  if (headerEnd === -1) {
    return "";
  }

  let body = afterType.slice(headerEnd + 2);

  const boundaryMatch = body.match(/\n--[^\n]+/);

  if (boundaryMatch) {
    body = body.slice(0, boundaryMatch.index);
  }

  const headers = afterType.slice(0, headerEnd);

  if (/Content-Transfer-Encoding:\s*base64/i.test(headers)) {
    body = decodeBase64(body);
  }

  if (/Content-Transfer-Encoding:\s*quoted-printable/i.test(headers)) {
    body = decodeQuotedPrintable(body);
  }

  return body;
}

function htmlToText(html) {
  try {
    const parser = new DOMParser();

    const document = parser.parseFromString(html, "text/html");

    document
      .querySelectorAll("script, style, head")
      .forEach((element) => element.remove());

    document
      .querySelectorAll("br")
      .forEach((element) => element.replaceWith("\n"));

    document.querySelectorAll("p, div, li").forEach((element) => {
      element.append("\n");
    });

    return document.body.textContent || "";
  } catch (error) {
    console.error("HTML parsing failed:", error);

    return html.replace(/<[^>]+>/g, " ");
  }
}

function cleanBody(body) {
  if (!body) {
    return "";
  }

  return body
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\0/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function decodeQuotedPrintable(value) {
  if (!value) {
    return "";
  }

  try {
    const joined = value.replace(/=\n/g, "");

    const bytes = [];

    for (let index = 0; index < joined.length; index += 1) {
      if (
        joined[index] === "=" &&
        /^[0-9A-Fa-f]{2}$/.test(joined.slice(index + 1, index + 3))
      ) {
        bytes.push(parseInt(joined.slice(index + 1, index + 3), 16));
        index += 2;
      } else {
        const encoded = new TextEncoder().encode(joined[index]);
        bytes.push(...encoded);
      }
    }

    return new TextDecoder("utf-8").decode(new Uint8Array(bytes));
  } catch {
    return value;
  }
}

function decodeBase64(value) {
  if (!value) {
    return "";
  }

  try {
    const cleaned = value.replace(/\s+/g, "");

    const binary = atob(cleaned);

    const bytes = Uint8Array.from(binary, (character) =>
      character.charCodeAt(0),
    );

    return new TextDecoder("utf-8").decode(bytes);
  } catch {
    return value;
  }
}

function decodeMimeWords(value) {
  if (!value) {
    return "";
  }

  let result = value;

  result = result.replace(/=\?UTF-8\?B\?([^?]+)\?=/gi, (match, encoded) => {
    try {
      return decodeBase64(encoded);
    } catch {
      return match;
    }
  });

  result = result.replace(/=\?UTF-8\?Q\?([^?]+)\?=/gi, (match, encoded) => {
    try {
      return decodeQuotedPrintable(encoded.replace(/_/g, " "));
    } catch {
      return match;
    }
  });

  return result;
}

export default EmailUploader;
