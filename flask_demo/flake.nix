{
  inputs.nixpkgs.url =
    "github:NixOS/nixpkgs/e0759a49733dfc3aa225b8a7423c00da6e1ecb67";
  outputs = { self, nixpkgs }:
    with nixpkgs.legacyPackages.x86_64-linux;
    {
      devShell.x86_64-linux = mkShell {
        buildInputs = [
          mysql
          (python3.withPackages (pypkg: with pypkg; [ flask mysql-connector ]))
        ];
        shellHook = ''
          dataDir=$(pwd)/database
          alias install="mysql_install_db -u mlatus --datadir=''${dataDir}"
          alias server="mysqld --defaults-file=/dev/null --skip-grant-tables --datadir=''${dataDir} --socket=''${dataDir}/socket --lower-case-table-names"
          alias shutdown="mysqladmin -u mlatus -p --socket=''${dataDir}/socket shutdown"
          alias client="mysql -u mlatus -p --socket=''${dataDir}/socket"
        '';
      };
    };
}
