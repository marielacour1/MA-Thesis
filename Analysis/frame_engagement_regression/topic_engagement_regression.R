suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
})

args <- commandArgs(trailingOnly = TRUE)
default_input_csv <- file.path(getwd(), "Datasets", "final_dataset.csv")
default_output_dir <- file.path(getwd(), "Analysis", "frame_engagement_regression")
default_frame_column <- "frame"
default_reference_frame <- "Nature/Tourism"
plot_font_family <- "Times New Roman"

if (.Platform$OS.type == "windows") {
  do.call(
    windowsFonts,
    setNames(list(windowsFont("Times New Roman")), "Times New Roman")
  )
}

if (length(args) < 1) {
  message("No command-line args detected. Falling back to default project paths based on getwd().")
  input_csv <- normalizePath(default_input_csv, winslash = "/", mustWork = TRUE)
  output_dir <- default_output_dir
  frame_column <- default_frame_column
  reference_frame <- default_reference_frame
} else {
  input_csv <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
  output_dir <- if (length(args) >= 2) args[[2]] else dirname(input_csv)
  frame_column <- if (length(args) >= 3) args[[3]] else default_frame_column
  reference_frame <- if (length(args) >= 4) args[[4]] else default_reference_frame
}
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

parse_numeric <- function(x) {
  x <- trimws(as.character(x))
  x <- gsub(",", "", x)
  x[x == ""] <- NA
  suppressWarnings(as.numeric(x))
}

tidy_lm <- function(model, dv_name) {
  s <- summary(model)
  coefs <- as.data.frame(s$coefficients)
  coefs$term <- rownames(coefs)
  rownames(coefs) <- NULL
  names(coefs)[1:4] <- c("estimate", "std_error", "t_value", "p_value")
  coefs$outcome <- dv_name

  intercept_row <- data.frame(
    term = "(Intercept)",
    estimate = coefs$estimate[coefs$term == "(Intercept)"],
    std_error = coefs$std_error[coefs$term == "(Intercept)"],
    t_value = coefs$t_value[coefs$term == "(Intercept)"],
    p_value = coefs$p_value[coefs$term == "(Intercept)"],
    outcome = dv_name,
    frame = levels(model$model$frame)[1],
    label = levels(model$model$frame)[1],
    is_reference = TRUE
  )

  frame_rows <- subset(coefs, term != "(Intercept)")
  if (nrow(frame_rows) > 0) {
    frame_rows$frame <- sub("^frame", "", frame_rows$term)
    frame_rows$label <- frame_rows$frame
    frame_rows$is_reference <- FALSE
  } else {
    frame_rows$frame <- character(0)
    frame_rows$label <- character(0)
    frame_rows$is_reference <- logical(0)
  }

  combined <- rbind(
    intercept_row[, c("outcome", "term", "frame", "label", "estimate", "std_error", "t_value", "p_value", "is_reference")],
    frame_rows[, c("outcome", "term", "frame", "label", "estimate", "std_error", "t_value", "p_value", "is_reference")]
  )
  combined$ci_low <- combined$estimate - 1.96 * combined$std_error
  combined$ci_high <- combined$estimate + 1.96 * combined$std_error
  combined
}

add_interpretable_effects <- function(df) {
  df$percent_estimate <- NA_real_
  df$percent_ci_low <- NA_real_
  df$percent_ci_high <- NA_real_
  df$interpretation <- ""

  log_rows <- df$outcome %in% c("log_views", "log_comments", "log_likes") & !df$is_reference
  df$percent_estimate[log_rows] <- (exp(df$estimate[log_rows]) - 1) * 100
  df$percent_ci_low[log_rows] <- (exp(df$ci_low[log_rows]) - 1) * 100
  df$percent_ci_high[log_rows] <- (exp(df$ci_high[log_rows]) - 1) * 100

  df$interpretation[log_rows] <- sprintf(
    "%+.1f%% compared with the reference frame",
    df$percent_estimate[log_rows]
  )

  df
}

wrap_frame_label <- function(x) {
  replacements <- c(
    "Climate Change and Natural Disaster" = "Climate Change",
    "Climate change and Natural Disaster" = "Climate Change",
    "Climate change and natural disaster" = "Climate Change",
    "Geopolitical and Strategic" = "Geopolitics",
    "Knowledge and Education" = "Knowledge/Facts",
    "Local Cultures and Everyday life" = "Indigenous Life",
    "Nature and Tourism" = "Nature/Tourism"
  )
  ifelse(x %in% names(replacements), replacements[x], x)
}

build_presentable_a4_plot <- function(df, reference_frame, font_family, scale = c("percent", "coefficient")) {
  scale <- match.arg(scale)
  plot_df <- subset(df, !is_reference & outcome %in% c("log_views", "log_comments", "log_likes"))
  if (nrow(plot_df) == 0) {
    warning("No non-reference coefficients available for the presentable A4 plot.")
    return(NULL)
  }

  outcome_labels <- c(
    log_views = "Views",
    log_comments = "Comments",
    log_likes = "Likes"
  )
  plot_df$outcome_label <- outcome_labels[plot_df$outcome]
  plot_df$outcome_label <- factor(plot_df$outcome_label, levels = c("Views", "Likes", "Comments"))

  frame_order <- unique(plot_df$frame[order(plot_df$estimate)])
  plot_df$label <- factor(wrap_frame_label(plot_df$frame), levels = wrap_frame_label(frame_order))

  if (scale == "percent") {
    estimate_col <- "percent_estimate"
    ci_low_col <- "percent_ci_low"
    ci_high_col <- "percent_ci_high"
    x_label <- "Percent difference"
    x_scale <- scale_x_continuous(labels = function(x) paste0(round(x), "%"))
  } else {
    estimate_col <- "estimate"
    ci_low_col <- "ci_low"
    ci_high_col <- "ci_high"
    x_label <- "Coefficient estimate"
    x_scale <- scale_x_continuous()
  }

  ggplot(plot_df, aes(x = .data[[estimate_col]], y = label)) +
    geom_vline(xintercept = 0, linetype = "dashed", linewidth = 0.35, color = "grey45") +
    geom_errorbarh(aes(xmin = .data[[ci_low_col]], xmax = .data[[ci_high_col]]), height = 0.16, linewidth = 0.45, color = "grey35") +
    geom_point(size = 2.3, color = "black") +
    facet_wrap(vars(outcome_label), ncol = 1, scales = "free_x") +
    labs(
      x = x_label,
      y = NULL
    ) +
    x_scale +
    scale_y_discrete(labels = function(x) x) +
    theme_minimal(base_family = font_family, base_size = 11) +
    theme(
      axis.title.x = element_text(size = 10.5, margin = margin(t = 5)),
      axis.text.x = element_text(size = 9.8),
      axis.text.y = element_text(size = 10.2, lineheight = 0.9),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      panel.spacing.y = unit(0.35, "cm"),
      strip.text = element_text(face = "bold", size = 11),
      strip.background = element_rect(fill = "white", color = "grey40", linewidth = 0.35),
      plot.margin = margin(8, 12, 8, 8)
    )
}

save_presentable_a4_plot <- function(plot, path, font_family) {
  if (is.null(plot)) {
    return(invisible(NULL))
  }

  png(
    filename = path,
    width = 6.5,
    height = 5.85,
    units = "in",
    res = 300,
    bg = "white",
    family = font_family
  )
  print(plot)
  dev.off()
}

df <- read.csv(input_csv, stringsAsFactors = FALSE, check.names = FALSE)
required <- c(frame_column, "view_count", "comment_count")
missing_cols <- setdiff(required, names(df))
if (length(missing_cols) > 0) {
  stop(paste("Missing required columns:", paste(missing_cols, collapse = ", ")))
}

df$frame <- trimws(df[[frame_column]])
df <- subset(df, nzchar(frame))
df$view_count_num <- parse_numeric(df$view_count)
df$comment_count_num <- parse_numeric(df$comment_count)
if ("video_like_count" %in% names(df)) {
  df$video_like_count_num <- parse_numeric(df$video_like_count)
} else {
  warning("No video_like_count column found. Skipping likes model.")
  df$video_like_count_num <- NA_real_
}
df$log_views <- log1p(df$view_count_num)
df$log_comments <- log1p(df$comment_count_num)
df$log_likes <- log1p(df$video_like_count_num)

frame_counts <- sort(table(df$frame), decreasing = TRUE)
frame_levels <- names(frame_counts)
if (!reference_frame %in% frame_levels) {
  stop(paste(
    "Reference frame not found:",
    reference_frame,
    "Available frames:",
    paste(frame_levels, collapse = ", ")
  ))
}
frame_levels <- c(reference_frame, setdiff(frame_levels, reference_frame))
df$frame <- factor(df$frame, levels = frame_levels)

views_model <- lm(log_views ~ frame, data = df)
comments_model <- lm(log_comments ~ frame, data = df)
likes_df <- subset(df, !is.na(log_likes))
likes_model <- if (nrow(likes_df) > 0) lm(log_likes ~ frame, data = likes_df) else NULL

views_tidy <- tidy_lm(views_model, "log_views")
comments_tidy <- tidy_lm(comments_model, "log_comments")
likes_tidy <- if (!is.null(likes_model)) tidy_lm(likes_model, "log_likes") else NULL
all_tidy <- rbind(views_tidy, comments_tidy, likes_tidy)
all_tidy <- add_interpretable_effects(all_tidy)

summary_path <- file.path(output_dir, "frame-engagement-regression-coefficients.csv")
write.csv(all_tidy, summary_path, row.names = FALSE)

presentable_plot <- build_presentable_a4_plot(all_tidy, reference_frame, plot_font_family, scale = "percent")
presentable_plot_path <- file.path(output_dir, "frame-engagement-regression-presentable-a4.png")
save_presentable_a4_plot(
  presentable_plot,
  presentable_plot_path,
  plot_font_family
)

coefficient_plot <- build_presentable_a4_plot(all_tidy, reference_frame, plot_font_family, scale = "coefficient")
coefficient_plot_path <- file.path(output_dir, "frame-engagement-regression-coefficients-presentable-a4.png")
save_presentable_a4_plot(
  coefficient_plot,
  coefficient_plot_path,
  plot_font_family
)

cat("Input CSV:", input_csv, "\n")
cat("Frame column:", frame_column, "\n")
cat("Rows used:", nrow(df), "\n")
if (!is.null(likes_model)) cat("Rows used for likes model:", nrow(likes_df), "\n")
cat("Reference frame:", reference_frame, "\n")
cat("Saved coefficients CSV to:", summary_path, "\n")
cat("Saved percent-difference A4 plot to:", presentable_plot_path, "\n")
cat("Saved coefficient-estimate A4 plot to:", coefficient_plot_path, "\n")
