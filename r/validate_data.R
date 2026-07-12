args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) stop("Usage: Rscript validate_data.R <csv>")
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("R package jsonlite is required")

path <- args[[1]]
d <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
issues <- list()

add_issue <- function(id, severity, description) {
  issues[[length(issues) + 1]] <<- list(issue_id=id, severity=severity, description=description)
}

if (!"USUBJID" %in% names(d)) {
  add_issue("DATA-USUBJID-MISSING", "High", "USUBJID is missing")
} else {
  if (any(is.na(d$USUBJID) | trimws(d$USUBJID) == "")) add_issue("DATA-USUBJID-NULL", "High", "USUBJID contains missing values")
  if (anyDuplicated(d$USUBJID) > 0) add_issue("DATA-USUBJID-DUP", "High", "USUBJID is not unique")
}

if ("ITTFL" %in% names(d)) {
  invalid <- setdiff(unique(d$ITTFL), c("Y", "N", ""))
  if (length(invalid) > 0) add_issue("DATA-ITTFL-CT", "Medium", paste("Unexpected ITTFL values:", paste(invalid, collapse=", ")))
}

result <- list(
  engine="R",
  rows=nrow(d),
  columns=ncol(d),
  passed=length(issues) == 0,
  issues=issues
)
cat(jsonlite::toJSON(result, auto_unbox=TRUE, null="null"))
