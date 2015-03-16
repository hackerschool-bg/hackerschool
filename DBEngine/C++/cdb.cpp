#include "cdb.h"

namespace cdb
{
    CDatabase::CDatabase()
    {
        m_th = NULL;
    }

    CDatabase::~CDatabase()
    {
        m_th = NULL;
    }

    bool CDatabase::CreateTable(const std::string& table, const std::string& columns)
    {
        std::string path = "Databases/" + toLower(table) + ".td";
        // Create database file
        printf("Creating table '%s' in '%s'\n", toLower(table).c_str(), path.c_str());
        FILE* pFile = fopen(path.c_str(), "wb");
        // Check for errors
        if (!pFile)
        {
            printf("Error - Unable to create table '%s': \n", toLower(table).c_str());
        }

        std::vector<std::string> columns_vector;
        split(columns, ';', columns_vector);

        // Write number of columns
        uint32_t numCols = columns_vector.size();
        fwrite(&numCols, sizeof(uint32_t), 1, pFile);

        // Parse the column definitions
        std::vector<std::string>::iterator it;
        for (it = columns_vector.begin(); it != columns_vector.end(); ++it)
        {
            std::vector<std::string> tokens;
            split((*it), ' ', tokens);
            printf("%-15s => %s\n", tokens[0].c_str(), tokens[1].c_str());

            std::string columnName = tokens[0];
            std::string columnType = tokens[1];

            // Write column type
            if (columnType == "integer")
            {
                int type = 0;
                fwrite(&type, sizeof(uint8_t), 1, pFile);
            }
            else if (columnType == "string")
            {
                int type = 1;
                fwrite(&type, sizeof(uint8_t), 1, pFile);
            }

            // Write column name length and column name
            int length = columnName.length();
            fwrite(&length, sizeof(uint32_t), 1, pFile);
            fwrite(columnName.c_str(), 1, length, pFile);

            if (ferror (pFile))
            {
                printf("Error - There was an error writing to the table.\n");
                return false;
            }
        }

        fclose(pFile);
        return true;
    }

    bool CDatabase::Open(const std::string& table)
    {
        if (m_th)
        {
            Close();
        }

        std::string path = "Databases/" + toLower(table) + ".td";
        m_th = fopen(path.c_str(), "r+b");
        if (!m_th)
        {
            printf("Error - Unable to open table '%s'.", toLower(table).c_str());
            return false;
        }
        return true;
    }

    void CDatabase::Close()
    {
        if (m_th)
        {
            fclose(m_th);
            m_th = 0;
        }
    }

    Cursor CDatabase::Select(const std::string& table, const ContentValues& where)
    {
        return Cursor();
    }

    int CDatabase::Delete(const std::string& table, const ContentValues& where)
    {
        return 0;
    }

    bool CDatabase::Insert(const std::string& table, const ContentValues& values)
    {

        return true;
    }

    int CDatabase::Update(const std::string& table, const ContentValues& where,
               const ContentValues& values)
    {
        return 0;
    }

    std::vector<std::string>& CDatabase::split(const std::string &s, char delim,
                                            std::vector<std::string>& elems)
    {
        std::stringstream ss(s);
        std::string item;
        while (std::getline(ss, item, delim))
        {
            elems.push_back(item);
        }
        return elems;
    }

    std::string CDatabase::toLower(const std::string& str)
    {
        std::string lower;
        std::string::const_iterator it;
        for (it = str.begin(); it != str.end(); ++it)
        {
            lower += (int(*it) < 97 ? int(*it) + 32 : (*it));
        }
        return lower;
    }

    bool CDatabase::fileExists (const std::string& name)
    {
        if (FILE *file = fopen(name.c_str(), "r")) {
            fclose(file);
            return true;
        } else {
            return false;
        }
    }
}
