#!/usr/bin/env Rscript
# Score locked homology test with AmpGram (n-gram ranger).
# Uses AmpGramModel + sourced predict internals (avoids AmpGram's shiny/devtools).
# Sequences shorter than 10 aa cannot form 10-mers and are skipped.

suppressPackageStartupMessages({
  library(AmpGramModel)
  library(biogram)
  library(pbapply)
  library(ranger)
  library(stringi)
  library(stats)
})

# From AmpGram/R/utils.R + predict.R — not library(AmpGram) (that package
# Imports shiny/devtools even for CLI predict).
count_longest <- function(x) {
  splitted_x <- strsplit(x = paste0(as.numeric(x > 0.5), collapse = ""),
                         split = "0")[[1]]
  len <- unname(sapply(splitted_x, nchar))
  if (length(len[len > 0]) == 0) {
    0
  } else {
    len[len > 0]
  }
}

calculate_statistics <- function(pred) {
  data.frame(fraction_true = mean(pred > 0.5),
             pred_mean = mean(pred),
             pred_median = median(pred),
             n_peptide = length(pred),
             n_pos = sum(pred > 0.5),
             pred_min = min(pred),
             pred_max = max(pred),
             longest_pos = max(count_longest(pred)),
             n_pos_10 = sum(count_longest(pred) >= 10),
             frac_0_0.2 = sum(pred <= 0.2) / length(pred),
             frac_0.2_0.4 = sum(pred > 0.2 & pred <= 0.4) / length(pred),
             frac_0.4_0.6 = sum(pred > 0.4 & pred <= 0.6) / length(pred),
             frac_0.6_0.8 = sum(pred > 0.6 & pred <= 0.8) / length(pred),
             frac_0.8_1 = sum(pred > 0.8 & pred <= 1) / length(pred))
}

find_ngrams <- function(seq, decoded_ngrams, len = 10) {
  end_pos <- len:length(seq)
  start_pos <- end_pos - len + 1
  res <- binarize(do.call(rbind, lapply(1L:length(end_pos), function(ith_mer_id) {
    ten_mer <- paste0(seq[start_pos[ith_mer_id]:end_pos[ith_mer_id]], collapse = "")
    stri_count(ten_mer, regex = decoded_ngrams)
  })))
  res
}

predict_ampgram <- function(object, newdata) {
  ngrams <- object[["imp_features"]]
  decoded_ngrams <- gsub(pattern = "_", replacement = ".",
                         x = decode_ngrams(ngrams), fixed = TRUE)
  all_preds <- pblapply(newdata, function(ith_seq) {
    ngram_count <- find_ngrams(seq = toupper(ith_seq), decoded_ngrams = decoded_ngrams)
    colnames(ngram_count) <- ngrams
    all_mers_pred <- predict(object[["rf_mers"]], ngram_count)[["predictions"]][, 2]
    single_prot_pred <- predict(object[["rf_peptides"]],
                                calculate_statistics(all_mers_pred))[["predictions"]][, 2]
    list(seq = ith_seq,
         all_mers_pred = all_mers_pred,
         single_prot_pred = single_prot_pred)
  })
  if (is.null(names(all_preds)))
    names(all_preds) <- paste0("seq", 1L:length(all_preds))
  all_preds
}

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) args[[1]] else {
  this <- tryCatch(normalizePath(sys.frame(1)$ofile), error = function(e) NA)
  if (is.na(this)) getwd() else normalizePath(file.path(dirname(this), "..", "..", ".."))
}

fasta <- file.path(root, "data", "splits", "test.fasta")
out_csv <- file.path(root, "reports", "benchmarks", "cohort_1_ampgram_scores.csv")
meta <- file.path(root, "reports", "benchmarks", "cache", "ampgram_meta.txt")
dir.create(dirname(out_csv), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(meta), recursive = TRUE, showWarnings = FALSE)

lines <- readLines(fasta, warn = FALSE)
ids <- character()
seqs <- character()
cur_id <- NULL
buf <- character()
flush_rec <- function() {
  if (!is.null(cur_id)) {
    ids <<- c(ids, cur_id)
    seqs <<- c(seqs, paste0(buf, collapse = ""))
  }
}
for (ln in lines) {
  if (startsWith(ln, ">")) {
    flush_rec()
    cur_id <- strsplit(substring(ln, 2), "\\s+")[[1]][1]
    buf <- character()
  } else {
    buf <- c(buf, ln)
  }
}
flush_rec()
seqs <- toupper(seqs)

aa20 <- strsplit("ACDEFGHIKLMNPQRSTVWY", "")[[1]]
ok <- vapply(seqs, function(s) {
  nchar(s) >= 10 && nchar(s) <= 200 && all(strsplit(s, "")[[1]] %in% aa20)
}, logical(1))

message(sprintf("AmpGram n=%d valid=%d skip=%d", length(ids), sum(ok), sum(!ok)))

to_aa <- function(s) strsplit(s, "")[[1]]
newdata <- lapply(seqs[ok], to_aa)
names(newdata) <- ids[ok]

t0 <- proc.time()[["elapsed"]]
preds <- predict_ampgram(AmpGram_model, newdata)
elapsed <- proc.time()[["elapsed"]] - t0

p <- rep(NA_real_, length(ids))
names(p) <- ids
for (nm in names(preds)) {
  sp <- preds[[nm]]$single_prot_pred
  p[[nm]] <- as.numeric(sp)[1]
}

df <- data.frame(id = ids, p_ampgram = as.numeric(p), stringsAsFactors = FALSE)
write.csv(df, out_csv, row.names = FALSE)
writeLines(sprintf("wall_s=%.3f\nskip=%d\nn=%d\nscored=%d", elapsed, sum(!ok), length(ids), sum(ok)), meta)
message(sprintf("wrote %s in %.1fs", out_csv, elapsed))
