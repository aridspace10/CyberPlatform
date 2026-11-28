export const COMMANDS = {
    touch: { description: "Create files or update their timestamps", groups: [{ name: "Files", options: [
        ["Update Modified Time", "Set a file's modification time without changing its access time."],
    ] }] },
    ls: { description: "List files and folders", groups: [{ name: "Listing", options: [
        ["Show Hidden", "Include hidden entries."], ["Long Listing", "Show detailed file information."],
    ] }] },
    cat: { description: "Read file contents", groups: [{ name: "Output", options: [
        ["Number Lines", "Add line numbers to the output."], ["Combine Files", "Read more than one file together."],
    ] }] },
    wc: { description: "Count text and file contents", groups: [{ name: "Counts", options: [
        ["Count Lines", "Count lines."], ["Count Words", "Count words."], ["Count Bytes", "Count bytes."], ["Count Characters", "Count characters."],
    ] }] },
    grep: { description: "Search text in files", groups: [
        { name: "Matching", options: [
            ["Case Insensitive", "Ignore letter case."], ["Match By Line", "Match a whole line."], ["Match By Word", "Match a whole word."],
            ["Invert Match", "Find lines that do not match."], ["Explicit Pattern", "Give the search pattern explicitly."], ["Regular Expression", "Search with a regular expression."],
        ] },
        { name: "Results", options: [
            ["Show Line Number", "Include matching line numbers."], ["Count Matches", "Show a match count."], ["Only Matching Text", "Show only matching text."],
            ["Show Filename", "Include file names in results."], ["Hide Filename", "Omit file names from results."], ["Find By Filename", "Search using a file name."],
        ] },
        { name: "Files and folders", options: [
            ["Recursive Search", "Search inside subfolders."], ["Include Files", "Search only included file names."],
            ["Exclude Files", "Skip matching file names."], ["Exclude Directories", "Skip matching folders."],
        ] },
    ] },
    sed: { description: "Edit text streams and files", groups: [
        { name: "Substitution", options: [
            ["Case Insensitive", "Ignore letter case when matching."], ["Replace All", "Replace every match on a line."],
            ["Replace Occurrence", "Replace a specific match on a line."], ["Regex Substitution", "Replace text matched by a regular expression."],
            ["Alternate Delimiter", "Use a different separator in an expression."],
        ] },
        { name: "Input and output", options: [
            ["Print Changes", "Show changed lines."], ["Quiet Output", "Suppress automatic output."],
            ["Expression Option", "Supply an editing expression."], ["Script File", "Read expressions from a script file."],
            ["Edit In Place", "Change a file directly."], ["Save a backup", "Keep a copy before editing a file."],
            ["Multiple Expressions", "Apply more than one expression."],
        ] },
        { name: "Addresses and lines", options: [
            ["Line Address", "Target a line number."], ["Pattern Address", "Target lines matching a pattern."],
            ["Last Line Address", "Target the final line."], ["Address Range", "Target a range of lines."],
            ["Negated Address", "Target lines outside an address."], ["Delete Lines", "Remove targeted lines."],
            ["Print Lines", "Print targeted lines."],
        ] },
    ] },
};

export const commandOptions = command => COMMANDS[command].groups.flatMap(group => group.options.map(([name]) => name));
